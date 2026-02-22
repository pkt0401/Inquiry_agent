# AI Talent Lab 문의하기 Agent - 답변 전략 정리

## 전략 개요

문의를 3가지 전략으로 분류:

1. **답변 안함** → 운영자 에스컬레이션 (티켓 자동 생성)
2. **Prompt 직접 답변** → 간단한 FAQ, LLM만으로 즉시 답변
3. **Tool Calling + RAG** → 복잡한 문의, 검색/분석 필요

---

## 1️⃣ 답변 안함 (운영자 에스컬레이션)

### 1-1. 개인 계정 조치 필요 (ACCOUNT_ACTION_REQUIRED)

**특징**:
- 사용자 계정 DB 직접 조작 필요
- Agent는 권한 없음

**예시**:
- "인증시험 버튼이 비활성화 되어있습니다"
- "[AI Literacy] 인증 시작하기 버튼 비활성화"
- "과제 제출 권한이 없습니다"

**Agent 조치**:
```
1. 운영자 티켓 자동 생성
2. 사용자에게 안내 메시지 발송
```

**안내 메시지 템플릿**:
```
안녕하세요.

해당 문의는 개인 계정 확인 및 시스템 조치가 필요한 사항입니다.
운영팀에 문의를 전달하였으며, 빠른 시일 내에 조치 후 답변드리겠습니다.

감사합니다.
```

---

### 1-2. 플랫폼 시스템 에러 (PLATFORM_SYSTEM_ERROR)

**특징**:
- 플랫폼 백엔드 문제
- 긴급 조치 필요

**예시**:
- "console 접근/python script 실행이 안됩니다"
- "파일 업로드가 안됩니다"

**Agent 조치**:
```
1. 운영자 티켓 자동 생성 (우선순위: 높음)
2. 사용자에게 안내 메시지 발송
```

**안내 메시지 템플릿**:
```
안녕하세요.

해당 문제는 플랫폼 시스템 점검이 필요한 사항입니다.
운영팀에서 긴급히 확인 중이며, 빠른 시일 내에 조치 후 답변드리겠습니다.

감사합니다.
```

---

### 1-3. 미분류 (UNCATEGORIZED)

**특징**:
- 명확한 분류 불가
- 보수적으로 운영자에게 전달

**예시**:
- 복잡하거나 애매한 문의
- 여러 주제가 섞인 문의

**Agent 조치**:
```
1. 운영자 검토 요청
2. 우선순위: 중간
```

---

## 2️⃣ Prompt 직접 답변 (간단한 FAQ)

### 2-1. 강의/수강 안내 (COURSE_INFO)

**특징**:
- 정적인 정보
- FAQ로 충분

**예시**:
- "문의하기 작성 가이드"
- "[Boot Camp] RAG 강의 Generation - Retriever 어디 있나요"
- "파이썬 기초 강의 어디서 들을 수 있나요?"

**필요 Context**:
- FAQ: 강의 목록 및 커리큘럼
- 수강 신청 방법

**Agent 조치**:
```
Prompt에 FAQ 포함 → LLM이 직접 답변 생성
```

---

### 2-2. 과제 제출 규정 (SUBMISSION_POLICY)

**특징**:
- 명확한 정책
- 과거 답변 일관됨

**예시**:
- "[Boot Camp] 최종 과제 기획 설계 문서 - 2단계(기획 설계서) 여러 차례 제출 가능 여부 문의"
- "Bootcamp 최종과제 기획 및 소스 코드 제출 관련 문의"
- "과제 재제출 가능한가요?"

**필요 Context**:
- FAQ: 과제 제출 규정
- 과거 답변 패턴

**답변 예시**:
```
안녕하세요.

최종과제의 기획 설계 문서와 소스코드는 여러번 제출 가능하십니다.
단, 마감 기한 이내에 제출하신 최종 버전으로 평가됩니다.

감사합니다.
```

**Agent 조치**:
```
Prompt에 FAQ + 과거 답변 패턴 포함 → LLM이 일관된 스타일로 답변
```

---

### 2-3. 서비스 이용 가이드 (SERVICE_GUIDE)

**특징**:
- 정적 문서
- 링크 제공으로 충분

**예시**:
- "IDE 사용 가이드 부탁드립니다"
- "Bootcamp 과제 작성 시 주의사항"

**필요 Context**:
- 가이드 문서 링크
- 공지사항

**Agent 조치**:
```
Prompt에 가이드 링크 포함 → LLM이 안내 메시지 + 링크 제공
```

---

### 2-4. 기능 개선/건의 (FEATURE_REQUEST)

**특징**:
- 단순 접수 확인
- 복잡한 처리 불필요

**예시**:
- "과제 부분별 점수 공개 요청 할게요?"

**필요 Context**:
- 건의 접수 정책

**답변 예시**:
```
안녕하세요.

소중한 의견 감사드립니다.
건의해주신 내용은 서비스 개선에 적극 반영하도록 하겠습니다.

감사합니다.
```

**Agent 조치**:
```
Prompt로 감사 메시지 생성 + 내부적으로 건의 사항 로그 저장
```

---

## 2️⃣-2 Prompt 직접 답변 (플랫폼 관련)

### 2-5. 플랫폼 API 사용법 (PLATFORM_API_USAGE)

**특징**:
- 플랫폼에서 제공하는 API 사용 방법
- 환경은 이미 설정됨, 사용법만 문의

**예시**:
- "Bootcamp 최종과제 api key 설정 문의"
- "플랫폼에서 OpenAI API 어떻게 사용하나요?"

**필요 Context**:
- FAQ: 플랫폼 API 사용 가이드
- 코드 예시

**Agent 조치**:
```
Prompt에 플랫폼 API 사용 가이드 포함 → LLM이 사용법 안내 + 코드 예시 제공
```

---

### 2-6. 강의 영상 재생 오류 (VIDEO_PLAYBACK_ERROR)

**특징**:
- 일반적인 트러블슈팅으로 해결 가능

**예시**:
- "강의 영상이 재생되지 않습니다"
- "비디오가 멈춥니다"

**필요 Context**:
- FAQ: 영상 재생 트러블슈팅
- 브라우저 권장 사항

**Agent 조치**:
```
Prompt에 FAQ 트러블슈팅 가이드 포함 → LLM이 해결 방법 안내
```

---

## 3️⃣ Tool Calling + RAG (복잡한 문의)

### 3-1. 과제 개발 방법 문의 (ASSIGNMENT_DEVELOPMENT)

**특징**:
- 개별 과제마다 다름
- 과거 사례 및 예시 필요

**예시**:
- "Azure OpenAI & LangChain 과제 개발 문의"
- "실습 환경에 패키지 설치 문의"
- "Bootcamp 최종과제 api key 설정 문의"

**필요 Context**:
- RAG: 과거 과제 Q&A
- Tool: 코드 예시 생성
- Tool: 참고 자료 검색

**필요 Tools**:
```python
search_similar_assignments(topic)  # 유사 과제 검색
generate_code_template(task)       # 코드 템플릿 생성
search_references(topic)            # 참고 자료 검색
```

**Agent Flow (LangGraph)**:
```
1. 질문 분석 (LLM)
2. search_similar_assignments() → 과거 유사 사례 검색 (RAG)
3. 과거 답변 + 코드 예시 결합 (LLM)
4. 답변 생성 및 신뢰도 평가 (LLM)
5. 신뢰도 높으면 → 자동 답변
   신뢰도 낮으면 → 운영자 검토
```

---

### 3-2. 코드 로직 에러 (CODE_LOGIC_ERROR)

**특징**:
- 사용자가 작성한 코드의 로직 문제
- 과거 유사 사례 및 디버깅 가이드 제공

**예시**:
- "TypeError가 발생합니다"
- "코드 실행 시 에러가 나요"
- "함수가 예상대로 동작하지 않습니다"

**필요 Context**:
- RAG: 과거 코드 에러 해결 사례
- Tool: 에러 메시지 분석
- Tool: 코드 디버깅 제안

**필요 Tools**:
```python
search_similar_code_errors(error_message)  # 유사 코드 에러 검색
analyze_code(code_snippet)                 # 코드 분석
suggest_fix(error_type, code)              # 수정 제안
```

**Agent Flow (LangGraph)**:
```
1. 에러 메시지 및 코드 파싱 (LLM)
2. search_similar_code_errors() → 유사 에러 검색 (RAG)
3. analyze_code() → 코드 분석 (Tool)
4. suggest_fix() → 수정 제안 (Tool)
5. 답변 생성 (LLM)
```

---

### 3-3. [제거됨] API 키 설정 에러

**제거 이유**: 플랫폼에서 이미 환경이 구성되어 있어 API 키 설정 문제는 발생하지 않음

→ 대신 **PLATFORM_API_USAGE**로 이동 (Prompt 직접 답변)

---

### 3-4. [제거됨] 라이브러리 설치/Import 에러

**제거 이유**: 플랫폼에서 필요한 라이브러리가 미리 설치되어 있어 설치 문제는 발생하지 않음

---

### 3-5. [이전 3-5] 강의 영상 재생 오류

**특징**:
- 에러 종류 다양
- 과거 사례 참고 필요

**필요 Context**:
- RAG: 과거 에러 해결 사례
- Tool: 에러 메시지 파싱
- Tool: Stack Overflow 검색 (선택)

**필요 Tools**:
```python
search_past_solutions(error_type)    # 과거 해결 사례
parse_error_message(error_text)      # 에러 메시지 파싱
search_stackoverflow(query)          # 외부 검색 (선택)
```

---

### 3-5. 강의 영상 재생 오류 (VIDEO_PLAYBACK_ERROR)

**특징**:
- 브라우저/네트워크 환경 다양
- 일반적 트러블슈팅 제공

**필요 Context**:
- RAG: 영상 재생 문제 해결 가이드
- Tool: 브라우저 호환성 확인
- Tool: 네트워크 문제 진단

**필요 Tools**:
```python
get_troubleshooting_guide(issue_type)  # 트러블슈팅 가이드
check_browser_compatibility()          # 브라우저 호환성
suggest_alternative_browsers()         # 대체 브라우저 제안
```

---

## 시스템 아키텍처 (LangGraph 기반)

```
┌─────────────────┐
│  새로운 문의     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  문의 분류 (Classifier)  │  ← LLM
└────────┬────────────────┘
         │
    ┌────┴────┬────────┬─────────┐
    │         │        │         │
    ▼         ▼        ▼         ▼
┌───────┐ ┌──────┐ ┌──────┐ ┌────────┐
│답변안함│ │Prompt│ │Tool  │ │미분류  │
│       │ │직접  │ │+RAG  │ │        │
└───┬───┘ └──┬───┘ └──┬───┘ └───┬────┘
    │        │        │         │
    ▼        ▼        ▼         ▼
┌────────┐ ┌─────────────────────┐ ┌────────┐
│티켓생성│ │ LLM 답변 생성        │ │운영자  │
│+안내   │ │ (FAQ/과거답변포함)  │ │검토    │
└────────┘ └─────────────────────┘ └────────┘
              │
              ▼
           ┌──────────────┐
           │ RAG 검색      │
           │ (유사사례)    │
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ Tool Calling  │
           │ (검색/분석)   │
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ 답변 생성     │
           └──────┬───────┘
                  │
                  ▼
           ┌──────────────┐
           │ 신뢰도 평가   │
           └──────┬───────┘
                  │
           ┌──────┴──────┐
           │             │
      높음 │             │ 낮음
           ▼             ▼
      ┌────────┐    ┌────────┐
      │자동답변│    │운영자  │
      │게시    │    │검토    │
      └────────┘    └────────┘
```

---

## LangGraph 노드 정의

### 1. Classifier Node
```python
def classify_inquiry(state):
    """문의 분류"""
    inquiry = state['inquiry']

    # LLM으로 분류
    classification = llm.invoke(f"""
    다음 문의를 분류하세요:
    제목: {inquiry['title']}
    내용: {inquiry['content']}

    분류 결과를 다음 중 하나로 답하세요:
    - ACCOUNT_ACTION_REQUIRED
    - SYSTEM_ERROR_USER_SPECIFIC
    - COURSE_INFO
    - SUBMISSION_POLICY
    - API_KEY_ERROR
    - LIBRARY_ERROR
    - ASSIGNMENT_DEVELOPMENT
    - ...
    """)

    state['label'] = classification
    return state
```

### 2. Route Decision
```python
def route_by_label(state):
    """라벨에 따라 다음 노드 결정"""
    label = state['label']

    if label in ['ACCOUNT_ACTION_REQUIRED', 'SYSTEM_ERROR_USER_SPECIFIC']:
        return 'escalate'
    elif label in ['COURSE_INFO', 'SUBMISSION_POLICY', 'SERVICE_GUIDE', 'FEATURE_REQUEST']:
        return 'prompt_direct'
    elif label in ['API_KEY_ERROR', 'LIBRARY_ERROR', 'ASSIGNMENT_DEVELOPMENT', ...]:
        return 'tool_rag'
    else:
        return 'uncategorized'
```

### 3. Prompt Direct Node
```python
def prompt_direct_response(state):
    """FAQ 기반 직접 답변"""
    inquiry = state['inquiry']
    label = state['label']

    # FAQ 로드
    faq = load_faq(label)
    past_responses = load_past_responses(label)

    # LLM으로 답변 생성
    response = llm.invoke(f"""
    다음은 과거 유사 질문에 대한 답변입니다:
    {past_responses}

    위 스타일을 참고하여 다음 질문에 답변하세요:
    {inquiry['content']}

    참고 FAQ:
    {faq}
    """)

    state['response'] = response
    state['confidence'] = 0.9  # Prompt 직접은 신뢰도 높음
    return state
```

### 4. Tool + RAG Node
```python
def tool_rag_response(state):
    """Tool Calling + RAG 답변"""
    inquiry = state['inquiry']
    label = state['label']

    # RAG: 유사 사례 검색
    similar_cases = vector_search(inquiry['content'])

    # Tool Calling
    if label == 'API_KEY_ERROR':
        error_guide = search_error_guide(inquiry['content'])
        official_docs = get_official_docs('openai api key')
        code_example = generate_code_example('python', 'set env variable')

        context = f"""
        유사 사례: {similar_cases}
        에러 가이드: {error_guide}
        공식 문서: {official_docs}
        코드 예시: {code_example}
        """

    # LLM으로 답변 생성
    response = llm.invoke(f"""
    다음 정보를 참고하여 답변하세요:
    {context}

    질문: {inquiry['content']}
    """)

    # 신뢰도 평가
    confidence = evaluate_confidence(response, similar_cases)

    state['response'] = response
    state['confidence'] = confidence
    return state
```

### 5. Confidence Check Node
```python
def check_confidence(state):
    """신뢰도 확인 후 자동 답변 or 운영자 검토"""
    if state['confidence'] > 0.7:
        return 'auto_post'
    else:
        return 'human_review'
```

---

## 필요한 Tools 구현

### Tool 1: 유사 사례 검색 (RAG)
```python
@tool
def search_similar_cases(query: str) -> str:
    """과거 유사 질문/답변 검색"""
    # Vector DB에서 검색
    results = vector_db.similarity_search(query, k=3)
    return results
```

### Tool 2: 에러 가이드 검색
```python
@tool
def search_error_guide(error_message: str) -> str:
    """에러 해결 가이드 검색"""
    # 에러 메시지 파싱
    parsed = parse_error(error_message)

    # 가이드 DB에서 검색
    guide = error_guide_db.get(parsed['error_type'])
    return guide
```

### Tool 3: 코드 예시 생성
```python
@tool
def generate_code_example(language: str, task: str) -> str:
    """코드 예시 생성"""
    template = code_template_db.get(language, task)
    return template
```

### Tool 4: 공식 문서 검색
```python
@tool
def get_official_docs(topic: str) -> str:
    """공식 문서 링크 검색"""
    docs = {
        'openai api key': 'https://platform.openai.com/docs/quickstart',
        'langchain': 'https://python.langchain.com/docs/',
        # ...
    }
    return docs.get(topic.lower())
```

---

## 구현 우선순위

### Phase 1: MVP (최소 기능)
1. ✅ Classifier: 문의 분류
2. ✅ Prompt 직접 답변: COURSE_INFO, SUBMISSION_POLICY
3. ✅ 에스컬레이션: ACCOUNT_ACTION_REQUIRED, SYSTEM_ERROR_USER_SPECIFIC

### Phase 2: RAG 추가
4. ⚠️ RAG 구축: 과거 문의 벡터화
5. ⚠️ Tool Calling: API_KEY_ERROR, LIBRARY_ERROR

### Phase 3: 완전 자동화
6. 🚀 신뢰도 평가 시스템
7. 🚀 자동 답변 게시
8. 🚀 운영자 피드백 루프

---

## 보수적 답변 기준

### 자동 답변 OK (신뢰도 > 0.7)
- Prompt 직접 답변 유형 (FAQ 기반)
- RAG에서 정확히 일치하는 과거 사례 존재
- Tool Calling 결과가 명확

### 운영자 검토 필요 (신뢰도 < 0.7)
- 유사 사례 없음
- 에러 메시지 불명확
- 여러 문제가 복합적
- 사용자가 추가 설명 필요

### 무조건 에스컬레이션
- 계정 조작 필요
- 개인 정보 확인 필요
- 시스템 백엔드 로그 필요

---

## 결론

**핵심 전략**:
1. **간단한 질문**: Prompt만으로 즉시 답변 (빠르고 비용 효율적)
2. **복잡한 질문**: Tool + RAG로 심층 분석 후 답변 (정확도 향상)
3. **위험한 질문**: 무조건 운영자 (안전 우선)

**보수적 접근**:
- 레이블별로 답변 여부 사전 결정
- 신뢰도 낮으면 자동으로 운영자 검토
- 에스컬레이션 시에도 안내 메시지로 사용자 대기 시간 단축
