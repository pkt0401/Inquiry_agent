# LLM 기반 문의 분류 실행 가이드

## 개요

GPT API를 사용하여 **LLM이 직접** 문의를 분석하고 답변 여부를 판단합니다.

### 규칙 기반 vs LLM 기반

| 항목 | 규칙 기반 | LLM 기반 |
|------|----------|---------|
| 분류 방식 | 키워드 매칭 | 의미 기반 이해 |
| 정확도 | 중간 | 높음 |
| 유연성 | 낮음 | 높음 |
| 속도 | 빠름 | 중간 |
| 비용 | 무료 | API 비용 |
| 유지보수 | 규칙 수정 필요 | 프롬프트만 수정 |

## 설치

```bash
# 패키지 설치
pip install -r requirements.txt

# 또는 개별 설치
pip install streamlit openai
```

## API 키 설정

### 방법 1: 환경변수 (권장)

**Windows (PowerShell)**:
```powershell
$env:OPENAI_API_KEY="your-api-key-here"
```

**Windows (CMD)**:
```cmd
set OPENAI_API_KEY=your-api-key-here
```

**Mac/Linux**:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 방법 2: .env 파일

`.env` 파일 생성:
```
OPENAI_API_KEY=your-api-key-here
```

### 방법 3: Streamlit에서 직접 입력

Streamlit 앱 실행 후 사이드바에서 API 키 입력 가능

## 실행 방법

### 1. Python 스크립트 직접 실행

```bash
python categorize_with_llm.py
```

테스트 샘플 3개를 분류합니다.

### 2. Streamlit 앱 실행 (LLM 기반)

```bash
streamlit run streamlit_demo_llm.py
```

브라우저에서 `http://localhost:8501` 자동 오픈

## 사용 방법

### 기본 사용

1. **API 키 설정** (환경변수 또는 사이드바)
2. **모델 선택** (사이드바)
   - `gpt-4o-mini`: 빠르고 저렴 (권장)
   - `gpt-4o`: 정확도 높음
   - `gpt-4-turbo`: 고성능
3. **문의 입력** (샘플 선택 또는 직접 입력)
4. **"LLM으로 분석 시작"** 버튼 클릭
5. **결과 확인**:
   - LLM 분류 결과 (레이블, 근거, 신뢰도)
   - 답변 전략 (답변안함/Prompt/RAG)
   - 필요 Context & Tools
   - 처리 Flow

### 고급 사용

#### Python 코드에서 사용

```python
from categorize_with_llm import categorize_with_llm

# 단일 문의 분류
result = categorize_with_llm(
    inquiry_title="과제 제출 문의",
    inquiry_content="최종과제는 여러 번 제출 가능한가요?",
    model="gpt-4o-mini"
)

print(f"레이블: {result['label_kr']}")
print(f"답변 여부: {result['should_respond']}")
print(f"전략: {result['strategy']}")
print(f"근거: {result['rationale']}")
print(f"신뢰도 레벨: {result['confidence_level']}")
```

#### 일괄 처리

```python
from categorize_with_llm import batch_categorize
import json

# 데이터 로드
with open('inquiry.json', 'r', encoding='utf-8') as f:
    inquiries = json.load(f)

# 일괄 분류
results = batch_categorize(inquiries, model="gpt-4o-mini")

# 결과 저장
with open('llm_classification_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
```

## LLM 분류 프롬프트

### 현재 프롬프트 구조

```
1. 환경 정보 설명
   - 클라우드 환경 제공
   - API 키/라이브러리 설치 문제 없음

2. 분류 카테고리 정의
   - 답변 안함 (3개)
   - Prompt 직접 (6개)
   - Tool + RAG (2개)

3. 분류 기준 설명

4. 출력 형식 (JSON)

5. 문의 내용 입력
```

### 프롬프트 수정

[categorize_with_llm.py](categorize_with_llm.py)의 `CLASSIFICATION_PROMPT` 변수를 수정하세요.

## 비용 예측

### GPT-4o-mini (권장)

- **입력**: $0.150 / 1M tokens
- **출력**: $0.600 / 1M tokens

**예상 비용** (문의 1건당):
- 입력: ~500 tokens × $0.150 / 1M = $0.000075
- 출력: ~100 tokens × $0.600 / 1M = $0.000060
- **총**: ~$0.00014 (약 0.19원)

**84건 전체 분류**:
- 약 $0.012 (약 16원)

### GPT-4o

- 약 10배 비용
- 84건 분류: 약 160원

### GPT-4-turbo

- 약 5배 비용
- 84건 분류: 약 80원

## 성능 최적화

### 1. 모델 선택

```python
# 빠르고 저렴
categorize_with_llm(title, content, model="gpt-4o-mini")

# 정확도 중요
categorize_with_llm(title, content, model="gpt-4o")
```

### 2. Temperature 조정

현재 `temperature=0.3` (일관성 중시)

더 창의적인 분류가 필요하면:
```python
response = client.chat.completions.create(
    model=model,
    temperature=0.7,  # 높이기
    ...
)
```

### 3. 캐싱

동일한 문의는 캐싱하여 API 호출 줄이기:

```python
import hashlib
import json

cache = {}

def categorize_with_cache(title, content, model="gpt-4o-mini"):
    # 캐시 키 생성
    cache_key = hashlib.md5(f"{title}:{content}".encode()).hexdigest()

    if cache_key in cache:
        return cache[cache_key]

    # LLM 분류
    result = categorize_with_llm(title, content, model)

    # 캐싱
    cache[cache_key] = result
    return result
```

### 4. 배치 처리

여러 문의를 동시에 처리:

```python
import asyncio
from openai import AsyncOpenAI

async def categorize_async(inquiries):
    client = AsyncOpenAI()
    tasks = [
        categorize_with_llm_async(inq['title'], inq['content'])
        for inq in inquiries
    ]
    return await asyncio.gather(*tasks)
```

## 트러블슈팅

### API 키 오류

```
Error: OPENAI_API_KEY environment variable not set
```

**해결**: 환경변수 설정 또는 Streamlit에서 직접 입력

### 모델 접근 오류

```
Error: You exceeded your current quota
```

**해결**: OpenAI 계정에 크레딧 충전

### JSON 파싱 오류

```
Error: Invalid JSON response
```

**해결**:
1. `response_format={"type": "json_object"}` 확인
2. 프롬프트에서 JSON 예시 명확히 제시

### 느린 응답

**해결**:
1. `gpt-4o-mini` 사용 (가장 빠름)
2. 캐싱 적용
3. 배치 처리 (비동기)

## 신뢰도 레벨 기반 처리

```python
result = categorize_with_llm(title, content)

confidence_level = result['confidence_level']

if confidence_level in ['very_high', 'high']:
    # 신뢰도 높음 → 자동 처리
    auto_process(result)
elif confidence_level == 'medium':
    # 신뢰도 중간 → 운영자 검토
    escalate_to_human(result)
else:  # low
    # 신뢰도 낮음 → 미분류
    mark_as_uncategorized(result)
```

## 다음 단계

### 1. 프롬프트 최적화

- A/B 테스트로 최적의 프롬프트 찾기
- Few-shot 예시 추가

### 2. Fine-tuning

- 과거 문의 데이터로 GPT 모델 Fine-tuning
- 비용 절감 및 정확도 향상

### 3. 하이브리드 접근

```python
# 1차: 규칙 기반 (빠름, 무료)
rule_result = categorize_with_rules(title, content)

if rule_result['confidence'] < 0.8:
    # 2차: LLM (정확함, 유료)
    llm_result = categorize_with_llm(title, content)
    return llm_result
else:
    return rule_result
```

### 4. 실시간 모니터링

- 분류 정확도 추적
- 비용 모니터링
- 에러율 분석

## 라이선스

내부 PoC 용도
