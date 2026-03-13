# AI Talent Lab 문의하기 Agent PoC

AI Talent Lab 문의하기 게시판에 자동 응답 Agent를 적용하기 위한 PoC.

---

## 파일 구조

```
70793/
├── inquiry_agent.py              # Agent 핵심 구현 (실행 파일)
├── knowledge_base.json           # 라벨별 큐레이션 Q&A + 사전 지식 (static, 거의 안 바뀜)
├── schedule.json                 # 기수별 일정 + 인증시험 일정 (dynamic, 기수마다 갱신)
├── compare_rag_modes.py          # Mode A vs B 비교 스크립트 (random sampling)
│
├── inquiry_all.json              # 전체 문의 게시물 (110건, 기존+3월 신규 병합)
├── inquiry_comment_all.json      # 전체 문의 댓글 (125건)
│
├── test/
│   ├── inquiry_new.json          # 3월 신규 문의 원본 (27건)
│   └── inquiry_comment_new.json  # 3월 신규 댓글 원본 (31건)
│
├── files.json                    # 첨부파일 메타데이터
├── files/                        # 실제 첨부파일
├── README.md                     # 본 파일
└── PoC_Report.md                 # PoC 상세 결과 (흐름 설계 + 분석)
```

> 운영자 ID: 2, 7, 61, 442, 2425, 3417

---

## 데이터 구성

| 구분 | 파일 | 문의 | 댓글 | 출처 |
|------|------|-----:|-----:|------|
| 전체 | inquiry_all.json + inquiry_comment_all.json | 110건 | 125건 | 기존 + 3월 신규 병합 |
| 신규(3월) | test/inquiry_new.json + test/inquiry_comment_new.json | 27건 | 31건 | 3월 최신 스크랩 |

---

## 실행 방법

### 1. 환경 준비

```bash
pip install openai faiss-cpu==1.7.4 "numpy<2"
```

`.env` 파일에 Azure OpenAI 설정:

```
# LLM - Azure OpenAI 02 (gpt-5.2)
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_ENDPOINT=https://<resource-02>.openai.azure.com/
AZURE_CHAT_DEPLOYMENT=gpt-5.2

# Embedding - Azure OpenAI 01 (text-embedding-3-large)
AZURE_OPENAI_EMBED_API_KEY=<key>
AZURE_OPENAI_EMBED_ENDPOINT=https://<resource-01>.openai.azure.com/
AZURE_EMBED_DEPLOYMENT=text-embedding-3-large
```

### 2. Agent 실행

```bash
cd 70793
python inquiry_agent.py
```

### 3. 출력 예시

```
테스트 1: 과제 제출 문의
────────────────────────────────────────────────────────────
[Label]       SUBMISSION_POLICY
[신뢰도]      very_high
[Strategy]    RAG 자동 답변 게시
[판단 근거]   과제 재제출 규정에 대한 명확한 문의

[생성된 답변]
안녕하세요, AI Talent Lab입니다.
최종과제의 기획 설계 문서와 소스코드는 여러 번 제출 가능합니다.
감사합니다.
```

---

## 처리 흐름 요약

```
문의 입력
  ↓
[Step 1] LLM 분류  →  label(10개) + confidence_level(4단계) + is_compound + sub_labels
          ↑ prior_knowledge + 라벨별 설명·예시 (knowledge_base.json) 주입
          ↑ 기수 일정·인증시험 일정 (schedule.json) 주입
  ↓
[Step 2] 코드가 strategy 결정
  ├─ 복합 문의 (is_compound) + sub_labels 中 Group1 포함
  │      →  human_review  (RAG 초안 + 운영자가 나머지 처리)
  ├─ 복합 문의 (is_compound) + sub_labels 全 Group2 + 2–3개
  │      →  tool_rag  (sub_label 각각 RAG 후 context 합산 → 통합 답변)
  │           └─ min(RAG score) < 0.65 → human_review 다운그레이드
  ├─ 복합 문의 (is_compound) + sub_labels 全 Group2 + 4개 이상
  │      →  human_review  (복잡도 초과, 운영자 검토)
  ├─ Group 1 라벨 OR confidence == low    →  no_response   (운영자 에스컬레이션)
  ├─ confidence == medium                 →  human_review  (RAG 초안 + 운영자 검토)
  └─ confidence == high / very_high       →  tool_rag      (RAG 자동 답변 게시)
                                               └─ RAG score < 0.65 → human_review 다운그레이드
  ↓
[Step 3] Label-aware RAG (tool_rag / human_review)
  ① FAISS 벡터 검색 (Azure text-embedding-3-large, 3072차원) — 동일 label 우선, cosine 유사도 top-3
     ※ 복합 문의 Group2 2-3개: sub_label별 각각 검색 후 context 합산, min(score)로 다운그레이드 판단
  ② 에러 솔루션 정규식 보완 (CODE_LOGIC_ERROR 또는 에러 키워드 감지 시)
  ③ 과정 정보 보완 (COURSE_INFO)
  ※ embeddings_cache.pkl 에 임베딩 결과 캐시 → 재실행 시 API 미호출
```

상세 내용은 [PoC_Report.md](PoC_Report.md) 참고.
