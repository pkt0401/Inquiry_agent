"""
AI Talent Lab 문의하기 Agent PoC

흐름:
  문의 입력
  → [Step 1] LLM 분류: label(10개) + confidence_level(4단계)
  → [Step 2] 코드가 strategy 결정:
       Group 1 라벨 또는 confidence==low  → no_response   (운영자 에스컬레이션)
       confidence==medium                 → human_review  (RAG 초안 + 운영자 검토)
       confidence==high/very_high + G2   → tool_rag      (RAG 자동 답변 게시)

RAG:
  - knowledge_base.json 에서 해당 label의 큐레이션 예제 우선 검색
  - 그 외 train history(inquiry.json + inquiry_comment.json)에서 유사 Q&A 보조 검색
  - 사전 지식 (prior_knowledge) 은 분류·답변 양쪽 프롬프트에 주입
"""

import json
import re
import os
import hashlib
import pickle
from datetime import datetime
import numpy as np
import faiss
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI


# ──────────────────────────────────────────────────────────────────
# HTML 전처리
# ──────────────────────────────────────────────────────────────────

class _HTMLTextExtractor(HTMLParser):
    _NEWLINE_TAGS = {'p', 'br', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                     'li', 'tr', 'pre', 'blockquote'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._NEWLINE_TAGS:
            self._parts.append('\n')

    def handle_endtag(self, tag):
        if tag in self._NEWLINE_TAGS:
            self._parts.append('\n')

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self) -> str:
        text = ''.join(self._parts)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()


def html_to_text(html: str) -> str:
    if not html:
        return ''
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


# ──────────────────────────────────────────────────────────────────
# 카테고리 Labels — 10개
# ──────────────────────────────────────────────────────────────────

class InquiryLabel(str, Enum):
    # Group 1 — no_response (운영자 에스컬레이션)
    ACCOUNT_ACTION_REQUIRED = "ACCOUNT_ACTION_REQUIRED"   # 개인 계정·권한·인증 직접 조치 필요
    PLATFORM_SYSTEM_ERROR   = "PLATFORM_SYSTEM_ERROR"     # 플랫폼 서버·시스템 에러
    VIDEO_PLAYBACK_ERROR    = "VIDEO_PLAYBACK_ERROR"      # 강의 영상 재생 안됨
    FEATURE_REQUEST         = "FEATURE_REQUEST"           # 기능 개선·건의
    UNCATEGORIZED           = "UNCATEGORIZED"             # 내용 불명확·분류 불가

    # Group 2 — tool_rag (RAG 기반 답변 시도)
    COURSE_INFO             = "COURSE_INFO"               # 강의 목록·수강 방법·커리큘럼
    SUBMISSION_POLICY       = "SUBMISSION_POLICY"         # 과제 제출 횟수·마감·재제출 규정
    SERVICE_GUIDE           = "SERVICE_GUIDE"             # 플랫폼 이용 방법·가이드
    ASSIGNMENT_DEVELOPMENT  = "ASSIGNMENT_DEVELOPMENT"    # 과제 구현 방법·개발 방향
    CODE_LOGIC_ERROR        = "CODE_LOGIC_ERROR"          # 코드 에러·API 호출·파싱 오류


GROUP1 = {
    InquiryLabel.ACCOUNT_ACTION_REQUIRED,
    InquiryLabel.PLATFORM_SYSTEM_ERROR,
    InquiryLabel.VIDEO_PLAYBACK_ERROR,
    InquiryLabel.FEATURE_REQUEST,
    InquiryLabel.UNCATEGORIZED,
}

GROUP2 = {
    InquiryLabel.COURSE_INFO,
    InquiryLabel.SUBMISSION_POLICY,
    InquiryLabel.SERVICE_GUIDE,
    InquiryLabel.ASSIGNMENT_DEVELOPMENT,
    InquiryLabel.CODE_LOGIC_ERROR,
}


# ──────────────────────────────────────────────────────────────────
# 신뢰도 / Strategy
# ──────────────────────────────────────────────────────────────────

class ConfidenceLevel(str, Enum):
    VERY_HIGH = "very_high"
    HIGH      = "high"
    MEDIUM    = "medium"
    LOW       = "low"


class Strategy(str, Enum):
    NO_RESPONSE   = "no_response"
    HUMAN_REVIEW  = "human_review"
    TOOL_RAG      = "tool_rag"


# 문의 등록일 기준 이 일수를 초과하면 운영자 에스컬레이션
STALE_DAYS = 30


# ──────────────────────────────────────────────────────────────────
# 데이터 클래스
# ──────────────────────────────────────────────────────────────────

@dataclass
class LLMClassification:
    label: InquiryLabel
    confidence_level: ConfidenceLevel
    rationale: str


@dataclass
class AgentResponse:
    strategy: Strategy
    should_respond: bool
    label: InquiryLabel
    confidence_level: ConfidenceLevel
    answer: Optional[str]
    reasoning: str


# ──────────────────────────────────────────────────────────────────
# VectorStore — FAISS + OpenAI Embedding 기반 유사도 검색
# ──────────────────────────────────────────────────────────────────

class VectorStore:
    EMBED_MODEL = "text-embedding-3-small"
    EMBED_DIM   = 1536  # text-embedding-3-small 기본 차원

    def __init__(self, openai_client: OpenAI, cache_path: str = None):
        self._client    = openai_client
        self._cache_path = cache_path
        self._emb_cache: Dict[str, List[float]] = self._load_cache()
        self.payloads: List[Dict] = []   # 각 벡터에 대응하는 메타데이터
        self._texts: List[str]   = []   # 임베딩할 원본 텍스트
        self.index: Optional[faiss.Index] = None

    # ── 캐시 I/O ─────────────────────────────────────────────────

    def _load_cache(self) -> Dict:
        if self._cache_path and os.path.exists(self._cache_path):
            with open(self._cache_path, 'rb') as f:
                return pickle.load(f)
        return {}

    def _save_cache(self):
        if self._cache_path:
            with open(self._cache_path, 'wb') as f:
                pickle.dump(self._emb_cache, f)

    def _key(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    # ── 문서 추가 / 인덱스 빌드 ──────────────────────────────────

    def add_document(self, text: str, payload: Dict):
        """문서 하나 등록. build_index() 호출 전까지 실제 임베딩은 안 함."""
        self._texts.append(text[:8000])
        self.payloads.append(payload)

    def build_index(self):
        """미캐시 텍스트를 배치 임베딩 후 FAISS IndexFlatIP 구축."""
        if not self._texts:
            return

        # 캐시에 없는 것만 배치 API 호출
        to_embed = [(self._key(t), t) for t in self._texts
                    if self._key(t) not in self._emb_cache]

        if to_embed:
            print(f"  임베딩 API 호출: {len(to_embed)}건 (캐시 미적중)")
            chunk = 100  # OpenAI 배치 최대
            for i in range(0, len(to_embed), chunk):
                batch = to_embed[i:i + chunk]
                resp = self._client.embeddings.create(
                    model=self.EMBED_MODEL,
                    input=[t for _, t in batch],
                )
                for (key, _), emb in zip(batch, resp.data):
                    self._emb_cache[key] = emb.embedding
            self._save_cache()
        else:
            print(f"  임베딩 캐시 100% 히트 ({len(self._texts)}건)")

        # FAISS 인덱스 구축
        matrix = np.array(
            [self._emb_cache[self._key(t)] for t in self._texts],
            dtype=np.float32,
        )
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix /= np.where(norms == 0, 1, norms)   # L2 정규화 → inner product = cosine

        self.index = faiss.IndexFlatIP(matrix.shape[1])
        self.index.add(matrix)
        print(f"  FAISS 인덱스 구축 완료: {self.index.ntotal}개 벡터")

    # ── 검색 ─────────────────────────────────────────────────────

    def search(self, query: str, label: str = None, top_k: int = 3) -> List[Dict]:
        """
        query를 임베딩 후 유사 문서 검색.
        label 지정 시 동일 라벨 문서를 우선 반환 (나머지는 label=None인 것만 보조).
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        # 쿼리 임베딩 (캐시 활용)
        key = self._key(query[:8000])
        if key not in self._emb_cache:
            resp = self._client.embeddings.create(model=self.EMBED_MODEL, input=query[:8000])
            self._emb_cache[key] = resp.data[0].embedding
            self._save_cache()

        q = np.array(self._emb_cache[key], dtype=np.float32)
        q /= max(np.linalg.norm(q), 1e-8)
        q = q.reshape(1, -1)

        k = min(top_k * 6, self.index.ntotal)
        scores, idxs = self.index.search(q, k)

        matched, others = [], []
        for score, i in zip(scores[0], idxs[0]):
            if i < 0:
                continue
            p = {**self.payloads[i], "score": float(score)}
            doc_label = self.payloads[i].get("label")
            if label and doc_label == label:
                matched.append(p)
            elif not doc_label:            # 라벨 미지정 문서는 보조로
                others.append(p)

        result = matched[:top_k]
        if len(result) < top_k:
            result += others[:top_k - len(result)]
        return result[:top_k]


# ──────────────────────────────────────────────────────────────────
# InquiryAgent
# ──────────────────────────────────────────────────────────────────

class InquiryAgent:
    ADMIN_IDS = {2, 7, 61, 442, 2425}

    def __init__(self, knowledge_base_path: str = None, api_key: str = None):
        self.kb = self._load_knowledge_base(knowledge_base_path)
        self.inquiry_history: List[Dict] = []
        self._client = OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY")
        )
        self.vector_store: Optional[VectorStore] = None

    # ── Knowledge Base 로드 ────────────────────────────────────────

    def _load_knowledge_base(self, path: str) -> Dict:
        """knowledge_base.json 로드. 없으면 빈 구조 반환."""
        if path and os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        # knowledge_base.json 이 같은 디렉토리에 있으면 자동 로드
        default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knowledge_base.json')
        if os.path.exists(default_path):
            with open(default_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"prior_knowledge": {}, "label_examples": {}, "error_solutions": []}

    # ── 유틸리티 ──────────────────────────────────────────────────

    def _strip_html(self, html: str) -> str:
        return html_to_text(html)

    def detect_language(self, text: str) -> str:
        if re.search(r'[가-힣]', text):
            return 'ko'
        elif re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
            return 'jp'
        return 'en'

    # ── 사전 지식 요약 (분류·답변 프롬프트 공통 주입) ────────────

    def _prior_knowledge_section(self) -> str:
        """knowledge_base.json의 prior_knowledge를 프롬프트용 텍스트로 변환."""
        pk = self.kb.get("prior_knowledge", {})
        if not pk:
            return ""

        lines = [
            f"## 플랫폼 사전 지식 ({pk.get('platform', 'AI Talent Lab')})",
            pk.get("description", ""),
            "",
            "### 교육 과정",
        ]
        for prog in pk.get("programs", []):
            lines.append(f"- {prog['name']} ({prog['level']}): {prog['description']}")
            if "modules" in prog:
                lines.append(f"  모듈: {', '.join(prog['modules'])}")
            fa = prog.get("final_assignment", {})
            if fa:
                lines.append(f"  최종과제: 강의 {fa.get('required_lectures')}개 수강 완료 후 시작 가능. "
                              f"재제출={'가능' if fa.get('submittable_multiple_times') else '불가'}. "
                              f"{fa.get('note', '')}")
        lines += ["", "### 주요 사실"]
        for fact in pk.get("important_facts", []):
            lines.append(f"- {fact}")

        return "\n".join(lines)

    # ── 분류 프롬프트용 라벨 설명 ─────────────────────────────────

    def _label_description_section(self) -> str:
        """knowledge_base.json의 label_examples를 분류 프롬프트용 텍스트로 변환."""
        label_examples = self.kb.get("label_examples", {})

        sections = []
        all_labels = [
            ("ACCOUNT_ACTION_REQUIRED", "운영자 직접 조치"),
            ("PLATFORM_SYSTEM_ERROR",   "플랫폼 서버·시스템 에러"),
            ("VIDEO_PLAYBACK_ERROR",    "강의 영상 재생 안됨"),
            ("FEATURE_REQUEST",         "기능 개선·건의"),
            ("UNCATEGORIZED",           "불명확·분류 불가"),
            ("COURSE_INFO",             "강의·커리큘럼 정보"),
            ("SUBMISSION_POLICY",       "과제 제출 정책"),
            ("SERVICE_GUIDE",           "플랫폼 이용 가이드"),
            ("ASSIGNMENT_DEVELOPMENT",  "과제 개발 방향"),
            ("CODE_LOGIC_ERROR",        "코드·API 오류"),
        ]

        for label_key, short_name in all_labels:
            info = label_examples.get(label_key, {})
            desc = info.get("description", "")
            patterns = info.get("typical_patterns", [])
            examples = info.get("qa_examples", [])[:2]  # 최대 2개 예시

            block = [f"- {label_key} ({short_name}): {desc}"]
            if patterns:
                block.append(f"  패턴: {' / '.join(patterns[:3])}")
            if examples:
                ex = examples[0]
                block.append(f"  예시: 제목=\"{ex['title']}\"")
            sections.append("\n".join(block))

        return "\n".join(sections)

    # ── Step 1: LLM 분류 ──────────────────────────────────────────

    def _llm_classify(self, inquiry: Dict) -> LLMClassification:
        title   = inquiry.get('title', '')
        content = self._strip_html(inquiry.get('content', ''))

        prior_knowledge = self._prior_knowledge_section()
        label_descs     = self._label_description_section()

        system_prompt = f"""너는 AI Talent Lab 문의 분류 Agent야.
문의를 읽고 아래 10개 카테고리 중 하나로 분류하고, 신뢰도를 판단해.

{prior_knowledge}

## 카테고리 (label) 정의

### Group 1 — 운영자 에스컬레이션 (RAG 답변 생성 안 함):
{label_descs.split('- COURSE_INFO')[0]}

### Group 2 — RAG 기반 답변 시도:
{"- COURSE_INFO" + label_descs.split('- COURSE_INFO')[1] if '- COURSE_INFO' in label_descs else ""}

## 분류 판단 기준

**ACCOUNT_ACTION_REQUIRED vs PLATFORM_SYSTEM_ERROR 구분:**
- 특정 사용자의 계정·권한·버튼 활성화를 운영자가 직접 바꿔줘야 → ACCOUNT_ACTION_REQUIRED
- 플랫폼 시스템 자체의 버그·장애 (콘솔 접근 불가, 무한 로딩, 배포 오류) → PLATFORM_SYSTEM_ERROR

**SUBMISSION_POLICY vs COURSE_INFO 구분:**
- 과제 제출 횟수·마감·재제출·평가 결과 발표 시기 → SUBMISSION_POLICY
- 강의 이수 조건·커리큘럼·수료 관계 → COURSE_INFO

**CODE_LOGIC_ERROR vs ASSIGNMENT_DEVELOPMENT 구분:**
- 코드 에러 메시지, API 호출 실패, 라이브러리 오류 → CODE_LOGIC_ERROR
- 과제 설계 방향, 아키텍처, 구현 접근법 → ASSIGNMENT_DEVELOPMENT

## 신뢰도 (confidence_level) 판단 요소:
① 문의 명확성     — 무엇을 묻는지 텍스트만 봐도 알 수 있는가
② 카테고리 단일성  — 10개 중 딱 하나에만 해당하는가
③ Agent 처리 가능성 — 시스템/계정 조치 없이 해결 가능한가
④ 필요 정보 충분성  — 답변하기에 충분한 정보가 문의에 담겨 있는가

레벨:
- very_high : ①②③④ 모두 충족
- high      : ①②③ 충족, ④ 일부 부족
- medium    : ①② 충족, ③ 불확실
- low       : ① 또는 ② 미충족

## 출력 형식 (JSON만 출력, 다른 텍스트 없이)
{{
  "label": "LABEL_NAME",
  "confidence_level": "very_high" | "high" | "medium" | "low",
  "rationale": "분류 근거 한 줄"
}}"""

        user_content = f"제목: {title}\n내용: {content}"

        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=300,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content},
                ],
            )
            raw = response.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            result = json.loads(json_match.group() if json_match else raw)

            label      = InquiryLabel(result.get("label", "UNCATEGORIZED"))
            confidence = ConfidenceLevel(result.get("confidence_level", "low"))
            return LLMClassification(
                label=label,
                confidence_level=confidence,
                rationale=result.get("rationale", ""),
            )

        except Exception as e:
            return LLMClassification(
                label=InquiryLabel.UNCATEGORIZED,
                confidence_level=ConfidenceLevel.LOW,
                rationale=f"분류 중 오류: {e}",
            )

    # ── Step 2: Strategy 결정 ─────────────────────────────────────

    @staticmethod
    def _is_stale(inquiry: Dict) -> Tuple[bool, str]:
        """
        inquiry의 create_dt가 STALE_DAYS일 초과이면 (True, 날짜문자열) 반환.
        create_dt 없거나 파싱 실패 시 (False, '') 반환.
        """
        create_dt_str = inquiry.get("create_dt", "")
        if not create_dt_str:
            return False, ""
        try:
            create_dt = datetime.strptime(create_dt_str, "%Y-%m-%d %H:%M:%S")
            days_elapsed = (datetime.now() - create_dt).days
            if days_elapsed > STALE_DAYS:
                return True, create_dt_str
        except (ValueError, TypeError):
            pass
        return False, ""

    def _determine_strategy(
        self, label: InquiryLabel, confidence: ConfidenceLevel
    ) -> Tuple[Strategy, bool]:
        if label in GROUP1 or confidence == ConfidenceLevel.LOW:
            return Strategy.NO_RESPONSE, False
        if confidence == ConfidenceLevel.MEDIUM:
            return Strategy.HUMAN_REVIEW, True
        return Strategy.TOOL_RAG, True

    # ── RAG: FAISS 벡터 검색 기반 KB 검색 ───────────────────────

    def _build_kb_context(self, label: InquiryLabel, inquiry_text: str) -> str:
        """
        FAISS 벡터 검색으로 해당 label의 유사 Q&A 최대 3개 + 에러 솔루션 보완.
        vector_store가 없으면 키워드 폴백 사용.
        """
        parts: List[str] = []
        text_lower = inquiry_text.lower()

        # ① FAISS 벡터 검색 (label-aware: 동일 라벨 우선)
        if self.vector_store and self.vector_store.index:
            hits = self.vector_store.search(inquiry_text, label=label.value, top_k=3)
            for hit in hits:
                q_short = hit.get("title", "")
                a_short = hit.get("answer", "")[:300]
                tag = f"[유사 예제 ({hit.get('type','?')} | score={hit['score']:.3f})]"
                parts.append(f"{tag}\nQ: {q_short}\nA: {a_short}")
        else:
            # 폴백: 키워드 토큰 overlap
            label_info = self.kb.get("label_examples", {}).get(label.value, {})
            inquiry_tokens = set(re.findall(r'[가-힣a-zA-Z0-9]+', text_lower))
            examples = sorted(
                label_info.get("qa_examples", []),
                key=lambda ex: len(inquiry_tokens & set(
                    re.findall(r'[가-힣a-zA-Z0-9]+',
                               (ex.get("title","") + ex.get("question","")).lower()))),
                reverse=True,
            )
            for ex in examples[:2]:
                parts.append(f"[라벨 예제: {label.value}]\nQ: {ex['title']}\n"
                             f"{ex['question'][:200]}\nA: {ex['answer'][:300]}")

        # ② 에러 솔루션 정규식 보완 (CODE_LOGIC_ERROR 또는 에러 키워드 감지 시)
        if label == InquiryLabel.CODE_LOGIC_ERROR or re.search(r'error|traceback|오류|에러', text_lower):
            for sol in self.kb.get("error_solutions", []):
                if re.search(sol["error_pattern"], inquiry_text, re.I):
                    parts.append(f"[에러 가이드]\n{sol['title']}: {sol['solution']}")
                    break

        # ③ 과정 정보 보완 (COURSE_INFO 라벨)
        if label == InquiryLabel.COURSE_INFO:
            for prog in self.kb.get("prior_knowledge", {}).get("programs", []):
                if any(k in text_lower for k in prog.get("keywords", [])):
                    fa = prog.get("final_assignment", {})
                    desc = f"{prog['name']} ({prog['level']}): {prog['description']}"
                    if fa:
                        desc += (f"\n  최종과제: 강의 {fa.get('required_lectures')}개 완료 후 시작. "
                                 f"{fa.get('note', '')}")
                    parts.append(f"[과정 정보]\n{desc}")
                    break

        return "\n\n".join(parts) if parts else "관련 KB 정보 없음"

    # ── 답변 생성 ─────────────────────────────────────────────────

    def _generate_answer(
        self,
        inquiry: Dict,
        label: InquiryLabel,
        confidence: ConfidenceLevel,
        kb_context: str,
    ) -> str:
        title   = inquiry.get('title', '')
        content = self._strip_html(inquiry.get('content', ''))
        lang    = self.detect_language(title + " " + content)
        is_draft = (confidence == ConfidenceLevel.MEDIUM)

        prior_knowledge = self._prior_knowledge_section()

        greetings = {
            'ko': '안녕하세요, AI Talent Lab입니다.',
            'en': 'Hello, this is AI Talent Lab.',
            'jp': 'こんにちは、AI Talent Labです。',
        }

        system_prompt = f"""너는 AI Talent Lab 문의 답변 Agent야.
{'※ 이 답변은 운영자 검토용 초안이야. [초안] 태그로 시작해.' if is_draft else ''}

{prior_knowledge}

[답변 규칙]
- 이 문의는 "{label.value}" 카테고리로 분류되었어.
- 언어: {'한국어' if lang == 'ko' else '영어' if lang == 'en' else '일본어'}
- 인사말로 시작: {greetings.get(lang, greetings['ko'])}
- 아래 KB 정보를 우선 참고해서 답변해. KB 정보에 있는 내용은 그대로 활용해.
- KB 정보에 없는 내용은 추측하지 말고 "확인 후 안내드리겠습니다"로 마무리해.
- 답변은 간결하고 명확하게. 마지막에 "감사합니다." 로 끝낼 것."""

        user_content = f"""[문의]
제목: {title}
내용: {content}

[KB 정보]
{kb_context}"""

        try:
            response = self._client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content},
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"답변 생성 오류: {e}"

    # ── 메인 처리 흐름 ────────────────────────────────────────────

    def process_inquiry(self, inquiry: Dict) -> AgentResponse:
        title   = inquiry.get('title', '')
        content = self._strip_html(inquiry.get('content', ''))
        inquiry_text = title + " " + content

        # Step 0: 날짜 만료 체크 (create_dt 기준 STALE_DAYS일 초과 시 에스컬레이션)
        stale, stale_dt = self._is_stale(inquiry)
        if stale:
            return AgentResponse(
                strategy=Strategy.NO_RESPONSE,
                should_respond=False,
                label=InquiryLabel.UNCATEGORIZED,
                confidence_level=ConfidenceLevel.LOW,
                answer=None,
                reasoning=f"문의 등록일({stale_dt})이 현재 기준 {STALE_DAYS}일 초과 — 운영자 에스컬레이션",
            )

        # Step 1: LLM 분류
        classification = self._llm_classify(inquiry)

        # Step 2: Strategy 결정
        strategy, should_respond = self._determine_strategy(
            classification.label, classification.confidence_level
        )

        if not should_respond:
            return AgentResponse(
                strategy=strategy,
                should_respond=False,
                label=classification.label,
                confidence_level=classification.confidence_level,
                answer=None,
                reasoning=classification.rationale,
            )

        # RAG 검색 후 답변 생성
        kb_context = self._build_kb_context(classification.label, inquiry_text)
        answer = self._generate_answer(
            inquiry, classification.label, classification.confidence_level, kb_context
        )

        # history 기록 (label 저장)
        self.inquiry_history.append({
            'inquiry': inquiry,
            'label': classification.label.value,
            'strategy': strategy.value,
            'has_admin_answer': False,
            'admin_answers': [],
        })

        return AgentResponse(
            strategy=strategy,
            should_respond=True,
            label=classification.label,
            confidence_level=classification.confidence_level,
            answer=answer,
            reasoning=classification.rationale,
        )

    # ── history 로드 (train + test 모두 지원) ─────────────────────

    def load_inquiry_history(
        self,
        inquiry_data: List[Dict],
        comment_data: List[Dict],
        pre_label: bool = False,
    ):
        """
        과거 문의 이력 로드 (RAG용).
        pre_label=True 이면 label_examples 키워드 패턴으로 라벨 사전 부여 (휴리스틱).
        로드 완료 후 자동으로 FAISS 벡터 인덱스를 구축함.
        """
        for inquiry in inquiry_data:
            admin_comments = [
                c for c in comment_data
                if c['inquiry_id'] == inquiry['id']
                and c.get('author_id') in self.ADMIN_IDS
            ]
            label = None
            if pre_label:
                label = self._heuristic_label(inquiry)

            self.inquiry_history.append({
                'inquiry':        inquiry,
                'label':          label,
                'has_admin_answer': len(admin_comments) > 0,
                'admin_answers':  admin_comments,
            })

        # history 로드 후 벡터 인덱스 자동 구축
        self.build_vector_index()

    def build_vector_index(self):
        """
        KB 큐레이션 예제 + 에러 솔루션 + history(운영자 답변 있는 것)를
        FAISS IndexFlatIP로 색인.
        embeddings_cache.pkl 에 임베딩 결과를 캐시하므로 재실행 시 API 미호출.
        """
        base = os.path.dirname(os.path.abspath(__file__))
        cache_path = os.path.join(base, "embeddings_cache.pkl")
        vs = VectorStore(self._client, cache_path=cache_path)

        # ① KB 큐레이션 Q&A
        for label_key, info in self.kb.get("label_examples", {}).items():
            for ex in info.get("qa_examples", []):
                text = ex.get("title", "") + "\n" + ex.get("question", "")
                vs.add_document(text, {
                    "label":  label_key,
                    "title":  ex.get("title", ""),
                    "answer": ex.get("answer", ""),
                    "type":   "kb_curated",
                })

        # ② 에러 솔루션
        for sol in self.kb.get("error_solutions", []):
            text = sol.get("title", "") + "\n" + sol.get("solution", "")
            vs.add_document(text, {
                "label":  "CODE_LOGIC_ERROR",
                "title":  sol.get("title", ""),
                "answer": sol.get("solution", ""),
                "type":   "error_solution",
            })

        # ③ History (운영자 답변 있는 것만)
        for h in self.inquiry_history:
            if not h.get("has_admin_answer") or not h.get("admin_answers"):
                continue
            inq   = h.get("inquiry", {})
            title = inq.get("title", "")
            body  = self._strip_html(inq.get("content", ""))[:500]
            ans   = self._strip_html(h["admin_answers"][0].get("content", ""))[:400]
            vs.add_document(title + "\n" + body, {
                "label":  h.get("label"),   # 휴리스틱 라벨 or None
                "title":  title,
                "answer": ans,
                "type":   "history",
            })

        print(f"벡터 인덱스 구축 중... (총 {len(vs._texts)}개 문서)")
        vs.build_index()
        self.vector_store = vs

    def _heuristic_label(self, inquiry: Dict) -> Optional[str]:
        """
        키워드 기반 라벨 휴리스틱 (LLM 호출 없이 사전 분류).
        정확도보다 속도 우선 — RAG history 검색에만 사용.
        """
        text = (inquiry.get('title', '') + ' ' +
                html_to_text(inquiry.get('content', ''))).lower()

        rules = [
            # (패턴, 라벨) — 순서가 중요: 더 구체적인 패턴 먼저
            # ① 계정·권한 직접 조치
            (r'인증.*버튼|버튼.*비활성|비활성화|수강.*버튼|접근.*안\s*됩|수강.*기간|권한.*변경|응시.*자격|입장.*불가|수강.*불가',
             "ACCOUNT_ACTION_REQUIRED"),
            # ② 플랫폼 시스템 오류
            (r'콘솔.*접근|python.*실행.*안|스크립트.*실행.*안|무한.*로딩|로딩.*무한|서버.*장애|ide.*실행|streamlit.*실행.*안|배포.*오류|파일.*실행.*안',
             "PLATFORM_SYSTEM_ERROR"),
            # ③ 영상 재생
            (r'영상.*재생|동영상.*로딩|강의.*영상.*안|동영상.*안\s*나|영상.*안\s*보',
             "VIDEO_PLAYBACK_ERROR"),
            # ④ 기능 건의
            (r'기능.*추가|개선.*요청|건의|ui.*변경|문구.*변경|다운로드.*요청|파일.*다운|공유.*요청',
             "FEATURE_REQUEST"),
            # ⑤ 코드·API 오류 (에러 메시지가 텍스트에 있음)
            (r'traceback|error:|keyerror|typeerror|modulenotfounderror|importerror|attributeerror'
             r'|api.?key|credentials|rate.?limit|오류.*발생|에러.*발생|exception|invoke.*안|파싱.*오류'
             r'|pip install|패키지.*설치|langchain.*오류|openai.*오류',
             "CODE_LOGIC_ERROR"),
            # ⑥ 과제 제출 정책
            (r'재제출|제출.*가능|마감|과제.*결과|수료.*결과|미이수|미수료|평가.*발표|결과.*발표|수료.*여부'
             r'|이수.*처리|제출.*완료.*확인|제출.*기간|과제.*기간',
             "SUBMISSION_POLICY"),
            # ⑦ 강의·커리큘럼 정보
            (r'커리큘럼|모듈.*구성|강의.*몇|강의.*완료.*과제|수강.*신청|ai bootcamp.*수료.*ai literacy'
             r'|수료.*처리|강의.*이수|수강.*방법|과정.*안내|bootcamp.*과정',
             "COURSE_INFO"),
            # ⑧ 플랫폼 사용 가이드
            (r'ide.*사용.*방법|ide.*가이드|콘솔.*사용|실행.*방법.*안내|과제.*제출.*절차|양식.*요청|사용.*방법.*문의',
             "SERVICE_GUIDE"),
            # ⑨ 과제 개발 방향·아키텍처
            (r'sub.?graph|아키텍처|구현.*방법|개발.*방향|rag.*구현|멀티.*에이전트|설계.*방법|폴더.*구조'
             r'|chain.*구성|agent.*구조|과제.*주제|서비스.*기획',
             "ASSIGNMENT_DEVELOPMENT"),
        ]

        for pattern, label in rules:
            if re.search(pattern, text):
                return label

        return None


# ──────────────────────────────────────────────────────────────────
# 유틸리티 / 메인
# ──────────────────────────────────────────────────────────────────

def load_json_file(filepath: str):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def _load_dotenv():
    """70793/ 또는 상위 디렉토리의 .env 파일에서 환경변수 로드"""
    base = os.path.dirname(os.path.abspath(__file__))
    for dirpath in (base, os.path.dirname(base)):
        env_path = os.path.join(dirpath, '.env')
        if os.path.exists(env_path):
            with open(env_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, _, val = line.partition('=')
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
            break


def main():
    print("=== AI Talent Lab 문의 Agent PoC ===\n")

    _load_dotenv()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[오류] OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("  70793/.env 파일을 만들고 OPENAI_API_KEY=sk-... 를 입력하세요.")
        return

    agent = InquiryAgent(api_key=api_key)

    base_path = os.path.dirname(os.path.abspath(__file__))

    # Train 데이터 로드
    inquiry_data = load_json_file(os.path.join(base_path, 'inquiry.json'))
    comment_data = load_json_file(os.path.join(base_path, 'inquiry_comment.json'))
    print(f"Train 문의 데이터: {len(inquiry_data)}건")

    # Test 데이터 로드 (있으면)
    test_inq_path = os.path.join(base_path, 'inquiry_test.json')
    test_cmt_path = os.path.join(base_path, 'inquiry_comment_test.json')
    if os.path.exists(test_inq_path):
        test_inquiry_data = load_json_file(test_inq_path)
        test_comment_data = load_json_file(test_cmt_path) if os.path.exists(test_cmt_path) else []
        print(f"Test 문의 데이터: {len(test_inquiry_data)}건")
        all_inquiries = inquiry_data + test_inquiry_data
        all_comments  = comment_data + test_comment_data
    else:
        all_inquiries = inquiry_data
        all_comments  = comment_data

    agent.load_inquiry_history(all_inquiries, all_comments, pre_label=True)
    print(f"총 history 로드: {len(agent.inquiry_history)}건 (라벨 사전 부여 완료)\n")
    print("Agent 준비 완료\n")

    # 테스트 케이스
    test_cases = load_json_file(os.path.join(base_path, 'test.json'))

    strategy_labels = {
        Strategy.NO_RESPONSE:  "운영자 에스컬레이션",
        Strategy.HUMAN_REVIEW: "RAG 초안 + 운영자 검토",
        Strategy.TOOL_RAG:     "RAG 자동 답변 게시",
    }

    for i, test_inquiry in enumerate(test_cases, 1):
        title   = test_inquiry.get('title', '')
        content = agent._strip_html(test_inquiry.get('content', ''))
        content_preview = content[:200].replace('\n', ' ').strip()

        print(f"\n{'='*60}")
        print(f"테스트 {i}: {title}")
        print(f"{'='*60}")
        print(f"[제목]   {title}")
        print(f"[내용]   {content_preview}{'...' if len(content) > 200 else ''}")
        print(f"[날짜]   {test_inquiry.get('create_dt', '없음')}")
        print(f"{'-'*60}")

        response = agent.process_inquiry(test_inquiry)

        print(f"[Label]       {response.label.value}")
        print(f"[신뢰도]      {response.confidence_level.value}")
        print(f"[Strategy]    {strategy_labels[response.strategy]}")
        print(f"[판단 근거]   {response.reasoning}")

        if response.answer:
            print(f"\n[생성된 답변]\n{response.answer}")


if __name__ == "__main__":
    main()
