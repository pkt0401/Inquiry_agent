# Streamlit 데모 실행 가이드

## 개요

AI Talent Lab 문의하기 Agent의 작동 과정을 시각적으로 확인할 수 있는 인터랙티브 데모입니다.

## 주요 기능

### 1. 문의 분석 시뮬레이션
- 문의 제목과 내용을 입력하면 실시간으로 분류
- 4단계 처리 과정 시각화:
  1. **문의 분류**: 어떤 유형으로 분류되는지
  2. **답변 전략 결정**: Prompt 직접 / Tool+RAG / 답변 안함
  3. **필요 Context & Tools**: 어떤 데이터와 도구가 필요한지
  4. **답변 생성**: 최종 답변 시뮬레이션

### 2. 샘플 문의 제공
- 8가지 대표적인 문의 유형 샘플
- 클릭 한 번으로 자동 입력

### 3. 실시간 통계
- 실제 데이터 기반 통계
- 답변 전략별 분포
- 문의 유형별 분포

## 설치 및 실행

### 1. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

또는

```bash
pip install streamlit
```

### 2. Streamlit 앱 실행

```bash
streamlit run streamlit_demo.py
```

### 3. 브라우저에서 확인

자동으로 브라우저가 열리며 `http://localhost:8501`로 접속됩니다.

## 사용 방법

### 방법 1: 샘플 문의 사용

1. 좌측 사이드바에서 샘플 선택
2. "🔍 분석 시작" 버튼 클릭
3. 4단계 처리 과정 확인

### 방법 2: 직접 입력

1. 사이드바에서 "직접 입력" 선택
2. 제목과 내용 입력
3. "🔍 분석 시작" 버튼 클릭
4. 결과 확인

## 데모 스크린샷 예시

### 과제 제출 규정 문의
- **분류**: 과제 제출 규정 (SUBMISSION_POLICY)
- **전략**: ✅ Prompt 직접 답변
- **결과**: FAQ 기반 즉시 답변

### 계정 권한 문제
- **분류**: 개인 계정 조치 필요 (ACCOUNT_ACTION_REQUIRED)
- **전략**: 🚫 답변 안함
- **결과**: 운영자 티켓 자동 생성 + 안내 메시지

### 과제 개발 문의
- **분류**: 과제 개발 방법 문의 (ASSIGNMENT_DEVELOPMENT)
- **전략**: 🔧 Tool + RAG
- **결과**: RAG 검색 → Tool 호출 → 답변 생성

## 시각화 요소

### 1. 색상 코드
- 🔵 **파란색**: 분류 단계
- 🟣 **보라색**: 전략 결정 단계
- 🟠 **주황색**: Context/Tools 단계
- 🟢 **초록색**: 답변 생성 단계

### 2. 상태 표시
- ✅ **초록색 체크**: Agent 답변 가능
- ❌ **빨간색 X**: 운영자 에스컬레이션
- ⚠️ **노란색 경고**: 조건부 또는 주의 필요

### 3. Flow 다이어그램
- 전체 Agent 처리 흐름을 ASCII 아트로 표시
- 각 단계별 분기 로직 시각화

## 실제 데이터 통계

하단에 실제 84건의 문의 데이터를 기반으로 한 통계가 표시됩니다:

- **총 문의 수**
- **Agent 답변 가능 건수**
- **운영자 에스컬레이션 건수**
- **답변 전략별 분포**
- **문의 유형별 분포**

## 기술 스택

- **Frontend**: Streamlit
- **Backend Logic**: categorize_inquiries.py
- **Data**: inquiry.json, inquiry_comment.json
- **Styling**: Custom CSS

## 주의사항

1. **데이터 파일 필요**: inquiry.json과 inquiry_comment.json이 같은 폴더에 있어야 통계가 표시됩니다.
2. **실시간 분석**: 입력한 내용을 실시간으로 분류하지만, 실제 LLM을 호출하지는 않습니다 (시뮬레이션).
3. **브라우저 호환성**: 최신 Chrome, Firefox, Edge, Safari 권장

## 향후 개선 사항

- [ ] 실제 LLM API 연동 (Claude API)
- [ ] RAG 검색 결과 실시간 표시
- [ ] 답변 품질 평가 기능
- [ ] 사용자 피드백 수집
- [ ] 다국어 지원 (일본어, 영어)

## 문제 해결

### Streamlit 설치 오류
```bash
pip install --upgrade pip
pip install streamlit
```

### 포트 충돌
```bash
streamlit run streamlit_demo.py --server.port 8502
```

### 데이터 파일 없음
현재 디렉토리에 `inquiry.json`과 `inquiry_comment.json`이 있는지 확인하세요.

## 라이선스

내부 PoC 용도로 제작되었습니다.
