"""
AI Talent Lab 문의하기 Agent 시각화 데모 (LLM 기반)

실행 방법:
1. 환경변수 설정: export OPENAI_API_KEY="your-api-key"
2. streamlit run streamlit_demo_llm.py
"""

import streamlit as st
import json
import time
import os
from categorize_with_llm import categorize_with_llm, strip_html_tags

# 페이지 설정
st.set_page_config(
    page_title="AI Talent Lab 문의 Agent 데모 (LLM)",
    page_icon="🤖",
    layout="wide"
)

# CSS 스타일
st.markdown("""
<style>
    .stAlert {
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .step-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 4px solid;
    }
    .step-classify {
        background-color: #e3f2fd;
        border-color: #2196f3;
    }
    .step-strategy {
        background-color: #f3e5f5;
        border-color: #9c27b0;
    }
    .step-context {
        background-color: #fff3e0;
        border-color: #ff9800;
    }
    .step-response {
        background-color: #e8f5e9;
        border-color: #4caf50;
    }
    .confidence-high {
        color: #4caf50;
        font-weight: bold;
    }
    .confidence-medium {
        color: #ff9800;
        font-weight: bold;
    }
    .confidence-low {
        color: #f44336;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# API 키 확인
if 'OPENAI_API_KEY' not in os.environ:
    st.error("⚠️ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
    st.info("환경변수를 설정하거나 사이드바에서 API 키를 입력하세요.")

    api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    if api_key:
        os.environ['OPENAI_API_KEY'] = api_key
        st.sidebar.success("✅ API 키가 설정되었습니다.")
    else:
        st.stop()

# 타이틀
st.title("🤖 AI Talent Lab 문의하기 Agent 데모 (LLM 기반)")
st.markdown("**GPT API**가 문의를 분석하고 답변 여부를 판단합니다.")

# 사이드바 - 설정
st.sidebar.header("⚙️ 설정")

model_choice = st.sidebar.selectbox(
    "GPT 모델 선택",
    ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
    index=0,
    help="gpt-4o-mini가 가장 빠르고 저렴합니다."
)

st.sidebar.divider()

# 사이드바 - 샘플 문의
st.sidebar.header("📋 샘플 문의")
sample_inquiries = {
    "과제 제출 규정": {
        "title": "[Boot Camp] 최종 과제 제출 문의",
        "content": "최종과제 기획 설계 문서와 소스코드는 여러 번 제출 가능한가요?"
    },
    "계정 권한 문제": {
        "title": "인증시험 버튼 비활성화",
        "content": "인증 시작하기 버튼이 비활성화 되어 인증시험을 칠 수 없습니다."
    },
    "플랫폼 시스템 에러": {
        "title": "console 접근 불가",
        "content": "console 접근이 안되고 python script 실행이 안됩니다."
    },
    "과제 개발 문의": {
        "title": "Azure OpenAI 과제 개발",
        "content": "Azure OpenAI & LangChain을 사용한 과제 개발 중인데 어떻게 구현해야 할지 모르겠습니다."
    },
    "플랫폼 API 사용법": {
        "title": "api key 설정 문의",
        "content": "플랫폼에서 OpenAI API를 어떻게 사용하나요? 설정 방법을 알려주세요."
    },
    "코드 에러": {
        "title": "TypeError 발생",
        "content": "코드 실행 시 TypeError가 발생합니다. 어떻게 해결하나요?"
    },
    "강의 문의": {
        "title": "파이썬 기초 강의",
        "content": "파이썬 기초 강의는 어디서 들을 수 있나요?"
    },
    "영상 재생 오류": {
        "title": "강의 영상 재생 안됨",
        "content": "강의 영상이 재생되지 않습니다. 해결 방법이 있나요?"
    }
}

selected_sample = st.sidebar.selectbox(
    "샘플 선택",
    ["직접 입력"] + list(sample_inquiries.keys())
)

# 메인 입력 영역
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 문의 입력")

    if selected_sample != "직접 입력":
        default_title = sample_inquiries[selected_sample]["title"]
        default_content = sample_inquiries[selected_sample]["content"]
    else:
        default_title = ""
        default_content = ""

    inquiry_title = st.text_input("제목", value=default_title)
    inquiry_content = st.text_area("내용", value=default_content, height=150)

    analyze_button = st.button("🔍 LLM으로 분석 시작", type="primary", use_container_width=True)

with col2:
    st.subheader("📊 LLM 분류 결과")

    if analyze_button and inquiry_title and inquiry_content:
        # 분석 시작
        with st.spinner(f"{model_choice} 모델로 분석 중..."):
            start_time = time.time()

            # LLM 분류 수행
            result = categorize_with_llm(inquiry_title, inquiry_content, model=model_choice)

            elapsed_time = time.time() - start_time

            # 1단계: 분류
            st.markdown("### 🎯 1단계: LLM 문의 분류")

            # 신뢰도 레벨 표시
            confidence_level = result.get('confidence_level', 'medium')
            confidence_map = {
                'very_high': ('confidence-high', '매우 높음'),
                'high': ('confidence-high', '높음'),
                'medium': ('confidence-medium', '중간'),
                'low': ('confidence-low', '낮음')
            }
            confidence_class, confidence_label = confidence_map.get(
                confidence_level,
                ('confidence-medium', '알 수 없음')
            )

            st.markdown(f"""
            <div class="step-box step-classify">
                <h4>{result['label_kr']} ({result['label']})</h4>
                <p><strong>근거:</strong> {result['rationale']}</p>
                <p><strong>신뢰도:</strong> <span class="{confidence_class}">{confidence_label} ({confidence_level})</span></p>
                <p style="color: gray; font-size: 0.9em;">분석 시간: {elapsed_time:.2f}초 | 모델: {model_choice}</p>
            </div>
            """, unsafe_allow_html=True)

            # 2단계: 답변 전략
            st.markdown("### 🎲 2단계: 답변 전략 결정")

            strategy_map = {
                'no_response': ('🚫 답변 안함', 'error'),
                'prompt_direct': ('✅ Prompt 직접 답변', 'success'),
                'tool_rag': ('🔧 Tool + RAG', 'info')
            }

            strategy_label, strategy_type = strategy_map.get(
                result['strategy'],
                ('❓ 미정', 'warning')
            )

            if result['should_respond']:
                st.success(f"**LLM 판단: Agent 답변 가능** → {strategy_label}")
            else:
                st.error(f"**LLM 판단: 운영자 에스컬레이션** → {result['action']}")

            st.markdown(f"""
            <div class="step-box step-strategy">
                <p><strong>전략:</strong> {result['strategy']}</p>
                <p><strong>조치:</strong> {result['action']}</p>
            </div>
            """, unsafe_allow_html=True)

            # 3단계: 필요한 Context/Tools (전략별)
            st.markdown("### 📚 3단계: 필요한 Context & Tools")

            if result['strategy'] == 'no_response':
                st.warning("운영자 에스컬레이션 - Context/Tools 불필요")

            elif result['strategy'] == 'prompt_direct':
                st.info("**Prompt 직접 답변 - 필요 Context:**")
                st.markdown("""
                - FAQ 데이터베이스
                - 과거 답변 패턴
                - 관련 가이드 문서
                """)

            elif result['strategy'] == 'tool_rag':
                st.info("**Tool + RAG - 필요 Context & Tools:**")
                st.markdown("""
                **Context:**
                - RAG: 과거 유사 사례 검색
                - FAQ: 관련 정보

                **Tools:**
                - `search_similar_cases(query)`
                - `analyze_inquiry(content)`
                - `generate_response(context)`
                """)

            # 4단계: 처리 Flow
            st.markdown("### 💬 4단계: 처리 Flow")

            if result['strategy'] == 'no_response':
                st.error("**운영자 티켓 자동 생성**")
                st.code("""
1. 티켓 생성 (우선순위 설정)
2. 사용자에게 안내 메시지 발송
3. 운영자 대시보드에 알림
                """, language='text')

            elif result['strategy'] == 'prompt_direct':
                st.success("**FAQ 기반 즉시 답변**")
                st.code("""
1. FAQ 데이터베이스 검색
2. 과거 유사 질문 답변 참조
3. LLM으로 답변 생성
4. 답변 게시
                """, language='text')

            elif result['strategy'] == 'tool_rag':
                st.info("**RAG + Tool Calling Flow**")
                st.code("""
1. 문의 내용 분석 (LLM)
2. RAG로 유사 사례 검색
3. Tool로 필요 정보 수집
4. LLM으로 답변 생성
5. 신뢰도 평가
   - 높음 → 자동 답변
   - 낮음 → 운영자 검토
                """, language='text')

# 하단 - LLM 분류 장점
with st.expander("🤔 왜 LLM 기반 분류를 사용하나요?", expanded=False):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### ✅ 장점

        1. **유연한 분류**
           - 키워드 매칭이 아닌 의미 기반 이해
           - 새로운 유형의 질문도 적절히 분류

        2. **정확도 향상**
           - 문맥을 고려한 판단
           - 애매한 경우 신뢰도로 표시

        3. **유지보수 용이**
           - 규칙 변경 없이 프롬프트만 수정
           - 새로운 카테고리 추가 쉬움

        4. **일관성**
           - 동일한 기준으로 판단
           - 사람보다 일관된 결과
        """)

    with col2:
        st.markdown("""
        ### ⚠️ 고려사항

        1. **비용**
           - API 호출 비용 발생
           - gpt-4o-mini 권장 (저렴)

        2. **속도**
           - 규칙 기반보다 느림
           - 캐싱으로 개선 가능

        3. **안정성**
           - API 장애 시 대비 필요
           - Fallback 로직 필요

        4. **프롬프트 엔지니어링**
           - 정확한 분류를 위한 프롬프트 최적화
           - 지속적인 개선 필요
        """)

# 하단 - 전체 Flow
with st.expander("📊 전체 LLM Agent Flow", expanded=False):
    st.markdown("""
    ```
    ┌─────────────────┐
    │  새로운 문의     │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────────────┐
    │  LLM 분류 (GPT API)     │  ← 답변 여부 판단
    │  - 레이블                │
    │  - 전략 (답변안함/Prompt/RAG) │
    │  - 신뢰도               │
    └────────┬────────────────┘
             │
        ┌────┴────┬────────┬─────────┐
        │         │        │         │
        ▼         ▼        ▼         ▼
    ┌───────┐ ┌──────┐ ┌──────┐ ┌────────┐
    │답변안함│ │Prompt│ │Tool  │ │신뢰도  │
    │       │ │직접  │ │+RAG  │ │낮음    │
    └───┬───┘ └──┬───┘ └──┬───┘ └───┬────┘
        │        │        │         │
        ▼        ▼        ▼         ▼
    ┌────────┐ ┌─────────────────────┐ ┌────────┐
    │티켓생성│ │ LLM 답변 생성        │ │운영자  │
    │+안내   │ │ (FAQ/RAG 기반)       │ │검토    │
    └────────┘ └─────────────────────┘ └────────┘
    ```
    """)

# 푸터
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>AI Talent Lab 문의하기 Agent PoC - LLM 기반 Streamlit 데모</p>
    <p>Powered by GPT API</p>
</div>
""", unsafe_allow_html=True)
