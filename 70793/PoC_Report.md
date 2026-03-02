# AI Talent Lab 문의하기 Agent PoC 보고서

## PoC 목표

1. 답변이 가능한 질문과 그렇지 않은 질문은 어떤 것이 있는지?
2. 특정 context가 있어야 답할 수 있는 질문이 있다면, 그 context는 무엇인지?
3. 과거 응답을 바탕으로 일관성 있게 참고해서 답변하게 만들 수 있는지?

---

## 1. 데이터 현황

| 항목 | Train | Test | 합계 |
|------|------:|-----:|-----:|
| 문의 수 | 84건 | 98건 | 182건 |
| 댓글 수 | 90건 | 112건 | 202건 |
| 운영자 답변 | 81건 | 97건 | 178건 |
| 답변 완료 문의 | 82건 (97%) | 93건 (95%) | — |

> **Train**: inquiry.json + inquiry_comment.json (기존 스크랩)
> **Test**: inquiry_test.json + inquiry_comment_test.json (C:/atl_scrape/inquiry_output 변환, inquiry_full.json → 동일 스키마)

### 문의 유형 분포 (Train 84건 기준)

| 유형 | 건수 | Agent 처리 방향 |
|------|-----:|----------------|
| 인증/버튼 비활성화 | 24건 | no_response (계정 직접 조치) |
| 강의/과제/실습 관련 | 35건 | tool_rag 또는 human_review |
| 기술 에러 (코드/API) | 15건 | tool_rag |
| 접근/접속 문제 | 5건 | no_response (플랫폼 이슈) |
| 기타 / 미분류 | 5건 | no_response |

---

## 2. 처리 흐름

### 전체 흐름도

```
문의 입력 (title + content, HTML → 텍스트 변환)
    │
    ▼
[Step 1] LLM 분류  (GPT-4o-mini)
    │  ↑ prior_knowledge (플랫폼 사전 지식) 주입
    │  ↑ 라벨별 설명 + 실제 예시 제목 주입 (knowledge_base.json)
    │
    │  label      → 10개 카테고리 중 하나
    │  confidence → very_high / high / medium / low
    │
    ▼
[Step 2] 코드가 strategy 결정
    │
    ├─ Group 1 라벨 OR confidence == low
    │      → no_response   (운영자 에스컬레이션, 답변 생성 없음)
    │
    ├─ confidence == medium
    │      → human_review  (RAG 검색 후 [초안] 답변 생성, 운영자 검토 후 게시)
    │      └── is_draft=True
    │
    └─ confidence == high / very_high  (Group 2)
           → RAG 검색 후 max_score 확인
                │
                ├─ max_score < 0.65  → human_review 다운그레이드 (초안 답변, 운영자 검토)
                │                        is_draft=True
                │
                └─ max_score ≥ 0.65  → tool_rag  (최종 답변 자동 게시)
                                         is_draft=False

[Step 3] RAG 검색  (_build_kb_context)
    FAISS 유사도 검색 (top_k×6 후보) → label-aware 필터링
    ① 동일 label 문서 우선 (kb_curated → history 순)
    ② 동일 label 부족 시 label=None history로 보충
    ③ CODE_LOGIC_ERROR 또는 에러 키워드 → error_solutions regex 보완
    ④ COURSE_INFO 라벨 → prior_knowledge.programs 과정 정보 추가
    → max_score 반환 (Step 2 다운그레이드 판단에 사용)
```

---

## 3. 카테고리 Labels — 10개

### Group 1 — `no_response` (운영자 에스컬레이션)

| Label | 해당 문의 | 실제 데이터 예시 |
|-------|----------|----------------|
| `ACCOUNT_ACTION_REQUIRED` | 개인 계정·권한·인증 직접 조치 필요 | "인증시험 버튼이 비활성화 되어있습니다.", "[AI Literacy] 인증 시작하기 버튼 비활성화", "AI Literacy 실습하기 문의(인증시험버튼 활성화)", "[긴급] 미국법인 인증 시험 활성화 필요 (1/29 오후 4시)" |
| `PLATFORM_SYSTEM_ERROR` | 플랫폼 서버·시스템 에러 | "console 접근/python script 실행이 안됩니다.", "[Boot Camp] 무한 로딩이 되고 있습니다 - 파이널 과제 제출", "최종과제 접속불가", "streamlit 서비스 개발 강의 중 실습 실행이 안됩니다." |
| `VIDEO_PLAYBACK_ERROR` | 강의 영상 재생 안됨 | "동영상 강의가 짤린 것 같아요", "강의 이어 듣기 재생이 않되네요" |
| `FEATURE_REQUEST` | 기능 개선·건의 | "최종 과제 영역에 '3개의 강의를 완료하면 과제를 시작할 수 있습니다'를 '전체 강의'로 변경 요청", "실습 파일 다운로드할 수 있게 공유 부탁 드립니다.", "최종 결과발표 전 사전으로 검토나 피드백을 받고싶습니다." |
| `UNCATEGORIZED` | 내용 불명확, 여러 주제 혼재 | "1", "삭제" |

### Group 2 — `tool_rag` (RAG 기반 답변 시도)

| Label | 해당 문의 | 실제 데이터 예시 |
|-------|----------|----------------|
| `COURSE_INFO` | 강의 목록, 수강 방법, 커리큘럼, 수료 조건 | "3개의 강의를 완료하면 과제를 시작할 수 있다고 했는데 안되요", "AI Bootcamp 수료 시, AI Literacy도 수료한 것으로 처리되나요?", "BootCamp 강의 복습 불가하나요?", "ai bootcamp 어디서 신청하면 되나요?" |
| `SUBMISSION_POLICY` | 과제 제출 횟수, 마감, 재제출 규정, 결과 발표 | "[Boot Camp] 최종 과제 제출 관련 문의 - 2단계(개발 명세서) 저장 이후 수정 가능 여부", "[Bootcamp] 9기 최종과제 평가결과", "과제 제출 완료 시점 문의", "과제가 제출이 되어버렸습니다.", "부트캠프 수료 문의 드립니다." |
| `SERVICE_GUIDE` | 플랫폼 이용 방법, 가이드 요청 | "IDE 사용법 가이드 부탁드립니다.", "Bootcamp 최종과제 기획 및 설계 최초 양식 문의", "새로 오픈한 코드리뷰 사용 문의", "실습 환경에 파이썬 패키지 설치 문의" |
| `ASSIGNMENT_DEVELOPMENT` | 과제 구현 방법, 개발 방향, 아키텍처 | "Azure OpenAI & LangChain 과제 개발 문의", "[Boot Camp] Sub-Graph 구조 관련 문의", "AI Bootcamp 최종과제 주제 문의드립니다.", "Bootcamp 최종과제 api key 관련 문의" |
| `CODE_LOGIC_ERROR` | 코드 에러, API 호출·파싱·rate limit 오류 | "[Boot Camp] RAG 강의 Generation - Retriever 관련 질문", "sqlite문의", "지금 인베딩 동시 요청 초과 인가요?", "에러 해결이 안돼요", "강의 중 소스코드 문의" |

---

## 4. 신뢰도(Confidence) — 4단계

### 판단 요소 (텍스트만으로)

| 번호 | 요소 | 판단 질문 |
|------|------|----------|
| ① | 문의 명확성 | 무엇을 묻는지 텍스트만 봐도 알 수 있는가? |
| ② | 카테고리 단일성 | 10개 중 딱 하나에만 해당하는가? |
| ③ | Agent 처리 가능성 | 시스템/계정 조치 없이 Agent가 해결 가능한가? |
| ④ | 필요 정보 충분성 | 답변하기에 충분한 정보가 문의에 담겨 있는가? |

### 레벨별 처리 방식

| 레벨 | 충족 조건 | 처리 방식 |
|------|----------|----------|
| `very_high` | ①②③④ 모두 | `tool_rag` → 자동 게시 |
| `high` | ①②③, ④ 일부 부족 | `tool_rag` → 자동 게시 |
| `medium` | ①②, ③ 불확실 | `human_review` → 초안 + 운영자 검토 |
| `low` | ① 또는 ② 미충족 | `no_response` → 에스컬레이션 |

### 혼동 잦은 라벨 쌍 구분 기준 (LLM 프롬프트에 명시)

| 혼동 쌍 | 구분 기준 |
|---------|----------|
| `ACCOUNT_ACTION_REQUIRED` vs `PLATFORM_SYSTEM_ERROR` | 특정 사용자 계정·버튼 활성화를 운영자가 직접 바꿔야 → ACCOUNT. 시스템 자체 버그·장애 → PLATFORM |
| `SUBMISSION_POLICY` vs `COURSE_INFO` | 제출 횟수·마감·평가 발표 → SUBMISSION. 강의 이수 조건·커리큘럼·수료 관계 → COURSE |
| `CODE_LOGIC_ERROR` vs `ASSIGNMENT_DEVELOPMENT` | 에러 메시지·API 오류 → CODE. 설계 방향·아키텍처·구현 접근법 → ASSIGNMENT |

---

## 5. LLM vs 코드 역할 분리

**LLM이 판단하는 것 (2가지)**
- `label` → 10개 카테고리 중 하나
- `confidence_level` → very_high / high / medium / low

**코드가 결정하는 것 (3가지)**
```python
# Step 2: 기본 strategy 결정
label in Group1 OR confidence == 'low'   → should_respond=False, strategy='no_response'
confidence == 'medium'                   → should_respond=True,  strategy='human_review'
confidence == 'very_high' / 'high'       → should_respond=True,  strategy='tool_rag'

# Step 3: RAG 유사도 기반 다운그레이드 (tool_rag만 해당)
strategy == 'tool_rag' AND max_rag_score < 0.65
    → strategy='human_review'  (RAG 예시 품질 부족 → 운영자 검토 필요)

# 답변 초안 여부: confidence가 아닌 최종 strategy 기준
is_draft = (strategy == 'human_review')  # [초안] 태그 부착 여부
```

---

## 6. 사전 지식 프롬프트 (Prior Knowledge)

`knowledge_base.json`의 `prior_knowledge` 섹션을 **분류 프롬프트**와 **답변 생성 프롬프트** 양쪽에 동일하게 주입.

### 포함 내용

| 항목 | 내용 |
|------|------|
| 플랫폼 소개 | AI Talent Lab: LG그룹 임직원 대상 AI 교육 플랫폼 |
| 과정 구성 | AI Literacy (LV1) / AI Bootcamp (LV2, 6개 모듈) / AI Master Project (LV3) |
| 최종과제 규정 | 강의 6개 완료 후 시작, 기획서+소스코드 각각 여러 번 제출 가능 |
| 인증 버튼 | 응시 대상자 + 응시 기간 중에만 활성화 → 비활성이 정상인 경우 있음 |
| IDE 정책 | 웹 기반 IDE 제공, 직접 venv 생성 비권장 (속도 저하·로딩 문제) |
| 결과 발표 | 수강 기간 종료 후 약 2주 뒤 이메일/Slack 안내 |
| 수료 관계 | AI Bootcamp 수료 시 AI Literacy 동시 수료 처리 |

### 효과

- 분류 시: "인증 버튼 비활성화 = 정상일 수 있음"을 LLM이 알고 ACCOUNT_ACTION_REQUIRED로 정확 분류
- 답변 시: KB 정보가 없어도 prior_knowledge만으로 정확한 답변 생성 가능

---

## 7. Label-aware RAG 설계

### 벡터 검색 스택

| 항목 | 내용 |
|------|------|
| 임베딩 모델 | OpenAI `text-embedding-3-small` (1536차원) |
| 인덱스 | FAISS `IndexFlatIP` (코사인 유사도, L2 정규화 후 inner product) |
| 캐시 | `embeddings_cache.pkl` — 재실행 시 API 미호출 |
| 검색 방식 | **label-aware** (기본): 동일 label 우선, label=None 보조<br>**similarity-only** (비교용): label 무시, 순수 유사도 상위 반환 |
| 다운그레이드 임계값 | `RAG_CONFIDENCE_THRESHOLD = 0.65` — 미만이면 tool_rag → human_review |

### RAG 검색 흐름 (label-aware 기본 모드)

```
FAISS 검색 (top_k × 6 = 18개 후보, 유사도 순)
    │
    ├─ 동일 label 문서 → matched (우선)
    ├─ label=None 문서 → others  (보조, matched 부족 시만)
    └─ 다른 label 문서 → 버림
    │
    ▼ 최대 top_k=3개 선택, max_score 추출

+ 에러 솔루션 regex 보완  (CODE_LOGIC_ERROR 또는 에러 키워드 감지 시)
+ 과정 정보 보완           (COURSE_INFO 라벨 시)
```

### label=None history란?

history 문의에 휴리스틱 라벨(9개 regex)을 부여하는데, 어떤 패턴도 매칭되지 않으면 `label=None`.
검색 시 동일 label 문서가 top_k에 못 미칠 때만 보조로 사용됨 (노이즈 최소화).

### 검색 모드 비교 (`compare_rag_modes.py`)

두 모드를 같은 문의에 대해 실행, 검색된 예시 + 생성 답변을 나란히 비교:

| 모드 | 설명 | 활성화 방법 |
|------|------|------------|
| Mode A (label-aware) | 동일 label 우선 필터 | 기본값 |
| Mode B (similarity-only) | label 무시, 순수 유사도 | `similarity_only=True` |

### FAISS 인덱스 구성 문서

| 출처 | 문서 수 | label 여부 |
|------|--------:|-----------|
| KB 큐레이션 Q&A (knowledge_base.json) | 26건 | 항상 있음 |
| 에러 솔루션 (knowledge_base.json) | 5건 | CODE_LOGIC_ERROR 고정 |
| Train/Test history (운영자 답변 있는 것) | ~178건 | 휴리스틱 라벨 (~90건) + None (~88건) |
| **합계** | **~209건** | |

### Heuristic Pre-labeling (history용)

Train + Test history 총 182건에 대해, LLM 호출 없이 정규식 패턴으로 사전 라벨 부여.
FAISS 검색 시 동일 label 문서 우선 필터링에 사용.

| 결과 | 건수 |
|------|-----:|
| 라벨 부여 완료 | ~90건 |
| 미분류 (None → 보조 결과로만 활용) | ~92건 |

---

## 8. 필요 Context 정의

### Tier 1 — 핵심 Knowledge Base (현재 구현)

| Context | 내용 | 사용 Label |
|---------|------|-----------|
| 사전 지식 (prior_knowledge) | 플랫폼·과정·규정 핵심 사실 | 전체 (분류+답변 프롬프트 공통 주입) |
| FAISS 벡터 검색 | KB 큐레이션 Q&A + 에러 솔루션 + history (~209건) — OpenAI text-embedding-3-small | 해당 Group 2 label |
| 에러 솔루션 정규식 | API 키, 패키지, 코드 에러 해결법 | `CODE_LOGIC_ERROR` 보완 |

### Tier 2 — 실시간 조회 (DB 연동 필요, 미구현)

| Context | 내용 | 필요 이유 |
|---------|------|----------|
| 사용자 수강 정보 | 등록 과정, 학습 진행률, 인증 응시 자격 | 개인화 답변 |
| 과제 제출 이력 | 제출 횟수, 마감 여부 | `SUBMISSION_POLICY` 정밀 답변 |

### Tier 3 — 고도화 (선택)

| Context | 내용 | 비고 |
|---------|------|------|
| 이미지 분석 | 에러 스크린샷 → 에러 메시지 추출 | Vision API 비용 증가 |

---

## 9. 다국어 지원

- **현재 데이터**: Train/Test 모두 100% 한국어
- **구현 상태**: 언어 자동 감지 (한국어 / 영어 / 일본어) + 언어별 인사말 분기 완료
- **검증 필요**: 영어·일본어 실제 문의 데이터 수집 후 테스트

---

## 10. 구현 파일 목록

| 파일 | 설명 |
|------|------|
| `inquiry_agent.py` | 메인 Agent (분류·RAG·답변 생성) |
| `knowledge_base.json` | 사전 지식 + 큐레이션 Q&A + 에러 솔루션 |
| `inquiry.json` / `inquiry_comment.json` | Train 데이터 (84건 문의 / 90건 댓글) |
| `inquiry_test.json` / `inquiry_comment_test.json` | Test 데이터 (98건 / 112건) |
| `test.json` | 18개 테스트 케이스 (중복 제거, 7개 label 커버) |
| `compare_rag_modes.py` | Mode A vs B 검색 예시 + 답변 비교 스크립트 |
| `pipeline_viz.html` | 전체 파이프라인 시각화 (브라우저에서 열기) |
| `embeddings_cache.pkl` | 임베딩 캐시 (재실행 시 API 미호출) |
| `requirements.txt` | `openai>=1.0.0`, `faiss-cpu==1.7.4`, `numpy>=1.24.0,<2` |

---

## 11. 다음 단계

| Phase | 내용 |
|-------|------|
| ~~Phase 2~~ | ~~Vector DB 구축~~ → **완료** (FAISS + OpenAI text-embedding-3-small, embeddings_cache.pkl 캐시) |
| **Phase 3** | DB 연동 — 사용자 수강 정보·과제 이력 실시간 조회 |
| **Phase 4** | Vision API 연동 — 에러 스크린샷 자동 분석 |
| **Phase 5** | 운영자 대시보드 — `human_review` 초안 검토·게시 UI |
