"""
LLM 기반 문의 분류 (GPT API 사용)

LLM이 문의를 분석하고 답변 여부를 판단합니다.
"""

import json
from openai import OpenAI
from html import unescape
from html.parser import HTMLParser
import os
from dotenv import load_dotenv  # 추가

# .env 파일에 기록된 OPENAI_API_KEY를 시스템 환경변수로 불러옵니다.
load_dotenv()

class MLStripper(HTMLParser):
    """HTML 태그 제거"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return ''.join(self.text)

def strip_html_tags(html):
    """HTML 태그 제거"""
    s = MLStripper()
    s.feed(html)
    return s.get_data().strip()

# OpenAI 클라이언트 초기화
client = OpenAI()  # OPENAI_API_KEY 환경변수 필요

# LLM 분류 프롬프트
CLASSIFICATION_PROMPT = """당신은 AI Talent Lab 문의하기 시스템의 분류 Agent입니다.

## 환경 정보
AI Talent Lab은 이미 구성된 클라우드 환경(IDE/Jupyter)을 제공합니다.
따라서 API 키, 라이브러리 설치 등의 환경 설정 문제는 발생하지 않습니다.

## 보수적 답변 원칙
**"확실할 때만 답변, 의심스러우면 사람에게"**
- 잘못된 답변보다 운영자 에스컬레이션이 안전함
- 개인정보/시스템 조치는 무조건 운영자

## 문의 분류 카테고리

### 1. 답변 안함 (운영자 에스컬레이션)
- **ACCOUNT_ACTION_REQUIRED**: 개인 계정 조치 필요 (예: 인증 버튼 비활성화, 권한 없음)
- **PLATFORM_SYSTEM_ERROR**: 플랫폼 시스템 에러 (예: console 접근 불가, 파일 업로드 안됨)
- **UNCATEGORIZED**: 미분류 (명확한 분류 불가)

### 2. Prompt 직접 답변 (FAQ 기반)
- **COURSE_INFO**: 강의/수강 안내
- **SUBMISSION_POLICY**: 과제 제출 규정
- **SERVICE_GUIDE**: 서비스 이용 가이드
- **FEATURE_REQUEST**: 기능 개선/건의
- **PLATFORM_API_USAGE**: 플랫폼 API 사용법
- **VIDEO_PLAYBACK_ERROR**: 강의 영상 재생 오류

### 3. Tool Calling + RAG (복잡한 문의)
- **ASSIGNMENT_DEVELOPMENT**: 과제 개발 방법 문의
- **CODE_LOGIC_ERROR**: 코드 로직 에러

## 답변 여부 판단 기준

### ✅ should_respond: true (답변 생성)
다음 조건을 **모두** 만족:
1. **신뢰도 레벨: very_high 또는 high**
2. **11개 카테고리 중 하나로 명확히 분류**
3. **다음 중 하나**:
   - FAQ로 즉시 답변 가능 (강의 목록, 제출 규정, 가이드)
   - 과거 사례 + Tool로 답변 가능 (코드 에러, 과제 개발)
4. **다음 모두 해당하지 않음**:
   - 개인 계정 DB 조작
   - 시스템 백엔드 조치
   - 관리자 권한 필요

### ❌ should_respond: false (답변 안함 → 운영자)
다음 중 **하나라도** 해당:
1. **신뢰도 레벨: medium 또는 low**
2. **개인 계정/시스템 조치 필요**
3. **정보 부족으로 답변 불가**
4. **잘못된 답변 시 위험성 있음**

### 🔍 미분류 (UNCATEGORIZED)
다음 중 **하나라도** 해당:
1. **신뢰도 레벨: low**
2. **11개 카테고리에 맞지 않음**
3. **여러 주제 혼재**
4. **문의 내용 불명확** (예: "안돼요", "이거 어떻게 해요?")

## 신뢰도 레벨 판단 기준
다음 4가지 요소를 종합적으로 고려하여 레벨 선택:
- **키워드 명확성**: 명확한 키워드 사용 여부
- **문의 구체성**: 구체적이고 명확한 설명
- **카테고리 적합도**: 하나의 카테고리에 명확히 속함
- **과거 사례 유사성**: 유사한 과거 사례 존재 가능성

### 신뢰도 레벨 정의:

**very_high** (매우 높음) - 자동 답변:
- 매우 명확한 키워드 (예: "과제 제출", "강의 위치")
- 구체적이고 명확한 문의
- 하나의 카테고리에 완벽히 매칭
- 과거 사례가 많을 것으로 예상

**high** (높음) - 자동 답변:
- 명확한 키워드 존재
- 구체적인 문의
- 명확한 카테고리 분류 가능
- 과거 사례 존재 가능성 높음

**medium** (중간) - 운영자 검토 필요:
- 일부 키워드 모호
- 문의 내용 일부 불명확
- 카테고리 경계선상
- 과거 사례 적을 가능성

**low** (낮음) - 미분류:
- 키워드 불명확 또는 없음
- 문의 내용 매우 불명확
- 여러 주제 혼재
- 카테고리 분류 어려움

## 출력 형식
다음 JSON 형식으로 답변하세요:

```json
{{
  "label": "LABEL_NAME",
  "label_kr": "한글 레이블",
  "should_respond": true/false,
  "strategy": "no_response" | "prompt_direct" | "tool_rag",
  "action": "구체적 조치 내용",
  "rationale": "분류 근거",
  "confidence_level": "very_high" | "high" | "medium" | "low"
}}
```

## 문의 내용

**제목**: {title}

**내용**: {content}

위 문의를 분석하고 JSON 형식으로 분류 결과를 제공하세요.
"""

def categorize_with_llm(inquiry_title: str, inquiry_content: str, model: str = "gpt-4o-mini") -> dict:
    """
    LLM을 사용한 문의 분류

    Args:
        inquiry_title: 문의 제목
        inquiry_content: 문의 내용
        model: 사용할 GPT 모델 (기본: gpt-4o-mini)

    Returns:
        분류 결과 딕셔너리
    """
    # HTML 태그 제거
    content_text = strip_html_tags(inquiry_content)

    # 프롬프트 구성
    prompt = CLASSIFICATION_PROMPT.format(
        title=inquiry_title,
        content=content_text
    )

    try:
        # GPT API 호출
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "당신은 문의 분류 전문가입니다. 항상 정확한 JSON 형식으로 답변하세요."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3  # 일관성 위해 낮은 temperature
        )

        # 결과 파싱
        result = json.loads(response.choices[0].message.content)

        # 기본값 설정
        if 'confidence_level' not in result:
            result['confidence_level'] = 'medium'

        return result

    except Exception as e:
        print(f"LLM 분류 오류: {e}")
        # 오류 시 기본 응답
        return {
            "label": "UNCATEGORIZED",
            "label_kr": "미분류 (오류)",
            "should_respond": False,
            "strategy": "no_response",
            "action": "운영자 검토",
            "rationale": f"LLM 분류 중 오류 발생: {str(e)}",
            "confidence_level": "low"
        }

def batch_categorize(inquiries: list, model: str = "gpt-4o-mini") -> list:
    """
    여러 문의를 일괄 분류

    Args:
        inquiries: 문의 목록 (각 문의는 title, content 포함)
        model: 사용할 GPT 모델

    Returns:
        분류 결과 리스트
    """
    results = []

    total = len(inquiries)
    for i, inquiry in enumerate(inquiries, 1):
        print(f"분류 중... ({i}/{total})")

        title = inquiry.get('title', '')
        content = inquiry.get('content', '')

        result = categorize_with_llm(title, content, model)

        results.append({
            'inquiry_id': inquiry.get('id'),
            'title': title,
            'content_preview': strip_html_tags(content)[:150],
            **result
        })

    return results

if __name__ == '__main__':
    # 테스트
    with open('test.json','r',encoding='utf-8') as f:
        test_inquiries = json.load(f)

    print("LLM 기반 분류 테스트\n")

    for inquiry in test_inquiries:
        print(f"제목: {inquiry['title']}")
        result = categorize_with_llm(inquiry['title'], inquiry['content'])
        print(f"분류: {result['label_kr']} ({result['label']})")
        print(f"답변 여부: {result['should_respond']}")
        print(f"전략: {result['strategy']}")
        print(f"근거: {result['rationale']}")
        print(f"신뢰도 레벨: {result['confidence_level']}")
        print("-" * 80)
