# AI Talent Lab 문의하기 Agent PoC

AI Talent Lab 문의하기 게시판에 자동 응답 Agent를 적용하기 위한 PoC.

---

## 파일 구조

```
70793/
├── inquiry_agent.py              # Agent 핵심 구현 (실행 파일)
├── knowledge_base.json           # 라벨별 큐레이션 Q&A + 사전 지식 (prior_knowledge)
├── convert_test_data.py          # inquiry_full.json → inquiry_test.json 변환 스크립트
│
├── inquiry.json                  # [Train] 문의 게시물 (84건)
├── inquiry_comment.json          # [Train] 문의 댓글 (90건, 운영자 답변 81건)
├── inquiry_test.json             # [Test]  문의 게시물 (98건, scrape 변환)
├── inquiry_comment_test.json     # [Test]  문의 댓글 (112건, 운영자 답변 97건)
│
├── test.json                     # 테스트 케이스 (6건)
├── files.json                    # 첨부파일 메타데이터
├── files/                        # 실제 첨부파일
├── README.md                     # 본 파일
└── PoC_Report.md                 # PoC 상세 결과 (흐름 설계 + 분석)
```

> 운영자 ID: 2, 7, 61, 442, 2425

---

## 데이터 구성

| 구분 | 파일 | 문의 | 댓글 | 출처 |
|------|------|-----:|-----:|------|
| Train | inquiry.json + inquiry_comment.json | 84건 | 90건 | 기존 스크랩 |
| Test  | inquiry_test.json + inquiry_comment_test.json | 98건 | 112건 | C:/atl_scrape/inquiry_output 변환 |

---

## 실행 방법

### 1. 환경 준비

```bash
pip install openai faiss-cpu==1.7.4 "numpy<2"
```

`.env` 파일에 API 키 설정:

```
OPENAI_API_KEY=sk-...
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
[Step 1] LLM 분류  →  label(10개) + confidence_level(4단계)
          ↑ prior_knowledge + 라벨별 설명·예시 (knowledge_base.json) 주입
  ↓
[Step 2] 코드가 strategy 결정
  ├─ Group 1 라벨 OR confidence == low    →  no_response   (운영자 에스컬레이션)
  ├─ confidence == medium                 →  human_review  (RAG 초안 + 운영자 검토)
  └─ confidence == high / very_high       →  tool_rag      (RAG 자동 답변 게시)
  ↓
[Step 3] Label-aware RAG (tool_rag / human_review)
  ① FAISS 벡터 검색 (OpenAI text-embedding-3-small) — 동일 label 우선, cosine 유사도 top-3
  ② 에러 솔루션 정규식 보완 (CODE_LOGIC_ERROR 또는 에러 키워드 감지 시)
  ③ 과정 정보 보완 (COURSE_INFO)
  ※ embeddings_cache.pkl 에 임베딩 결과 캐시 → 재실행 시 API 미호출
```

상세 내용은 [PoC_Report.md](PoC_Report.md) 참고.
