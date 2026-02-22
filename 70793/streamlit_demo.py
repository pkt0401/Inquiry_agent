"""
AI Talent Lab 문의하기 Agent 시각화 데모

실행 방법:
streamlit run streamlit_demo.py
"""

import streamlit as st
import json
import time
from categorize_inquiries import categorize_inquiry, strip_html_tags

# 페이지 설정
st.set_page_config(
    page_title="AI Talent Lab 문의 Agent 데모",
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
</style>
""", unsafe_allow_html=True)

# 타이틀
st.title("🤖 AI Talent Lab 문의하기 Agent 데모")
st.markdown("문의 내용을 입력하면 Agent가 어떻게 분류하고 답변하는지 시각적으로 확인할 수 있습니다.")

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

    analyze_button = st.button("🔍 분석 시작", type="primary", use_container_width=True)

with col2:
    st.subheader("📊 분류 결과")

    if analyze_button and inquiry_title and inquiry_content:
        # 분석 시작
        with st.spinner("문의를 분석하고 있습니다..."):
            time.sleep(0.5)  # 시각적 효과

            # 더미 inquiry 객체 생성
            inquiry = {
                'title': inquiry_title,
                'content': inquiry_content
            }

            # 분류 수행
            result = categorize_inquiry(inquiry, [])

            # 1단계: 분류
            st.markdown("### 🎯 1단계: 문의 분류")
            st.markdown(f"""
            <div class="step-box step-classify">
                <h4>{result['label_kr']} ({result['label']})</h4>
                <p><strong>근거:</strong> {result['rationale']}</p>
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
                st.success(f"**Agent 답변 가능**: {strategy_label}")
            else:
                st.error(f"**운영자 에스컬레이션**: {result['action']}")

            st.markdown(f"""
            <div class="step-box step-strategy">
                <p><strong>전략:</strong> {result['strategy']}</p>
                <p><strong>조치:</strong> {result['action']}</p>
            </div>
            """, unsafe_allow_html=True)

            # 3단계: 필요한 Context/Tools
            st.markdown("### 📚 3단계: 필요한 Context & Tools")

            if 'required_context' in result:
                st.markdown("**필요한 Context:**")
                for ctx in result['required_context']:
                    st.markdown(f"- {ctx}")

            if 'tools_needed' in result:
                st.markdown("**필요한 Tools:**")
                for tool in result['tools_needed']:
                    st.code(tool, language='python')

            # 4단계: 답변 생성 시뮬레이션
            st.markdown("### 💬 4단계: 답변 생성")

            if result['strategy'] == 'no_response':
                # 에스컬레이션
                if 'response_template' in result:
                    st.warning("**운영자 티켓 자동 생성 및 안내 메시지 발송**")
                    st.markdown(f"""
                    <div class="step-box step-response">
                        {result['response_template'].replace(chr(10), '<br>')}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning("운영자에게 문의를 전달합니다.")

            elif result['strategy'] == 'prompt_direct':
                # Prompt 직접 답변
                st.success("**FAQ 기반 즉시 답변**")

                if 'example_response' in result:
                    st.markdown(f"""
                    <div class="step-box step-response">
                        {result['example_response'].replace(chr(10), '<br>')}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("FAQ 데이터베이스에서 답변을 검색하여 제공합니다.")

            elif result['strategy'] == 'tool_rag':
                # Tool + RAG
                st.info("**RAG 검색 + Tool 호출 중...**")

                with st.expander("🔍 상세 처리 과정", expanded=True):
                    if result['label'] == 'ASSIGNMENT_DEVELOPMENT':
                        st.markdown("""
                        1. 과거 유사 과제 검색 (RAG)
                        2. 관련 코드 템플릿 생성 (Tool)
                        3. 참고 자료 검색 (Tool)
                        4. 답변 생성 (LLM)
                        5. 신뢰도 평가
                        """)
                    elif result['label'] == 'CODE_LOGIC_ERROR':
                        st.markdown("""
                        1. 에러 메시지 분석 (LLM)
                        2. 유사 에러 사례 검색 (RAG)
                        3. 코드 분석 (Tool)
                        4. 수정 제안 생성 (Tool)
                        5. 답변 생성 (LLM)
                        """)
                    else:
                        st.markdown("""
                        1. 문의 내용 분석 (LLM)
                        2. RAG로 유사 사례 검색
                        3. Tool로 필요한 정보 수집
                        4. 답변 생성 (LLM)
                        5. 신뢰도 평가
                        """)

                st.success("답변 생성 완료 (시뮬레이션)")

# 하단 - 전체 Flow 다이어그램
with st.expander("📊 전체 Agent Flow 다이어그램", expanded=False):
    st.markdown("""
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
    └────────┘ └─────────┬───────────┘ └────────┘
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
    """)

# 하단 - 통계
st.divider()
st.subheader("📈 분류 통계 (실제 데이터)")

# 실제 데이터 로드
try:
    with open('inquiry.json', 'r', encoding='utf-8') as f:
        inquiries = json.load(f)

    with open('inquiry_comment.json', 'r', encoding='utf-8') as f:
        all_comments = json.load(f)

    # 통계 계산
    label_counts = {}
    strategy_counts = {'no_response': 0, 'prompt_direct': 0, 'tool_rag': 0}

    for inquiry in inquiries:
        comments = [c for c in all_comments if c.get('inquiry_id') == inquiry.get('id')]
        result = categorize_inquiry(inquiry, comments)

        label = result['label_kr']
        strategy = result['strategy']

        label_counts[label] = label_counts.get(label, 0) + 1
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("총 문의", len(inquiries))

    with col2:
        agent_can_respond = strategy_counts['prompt_direct'] + strategy_counts['tool_rag']
        st.metric("Agent 답변 가능", agent_can_respond)

    with col3:
        st.metric("운영자 에스컬레이션", strategy_counts['no_response'])

    # 상세 통계
    st.markdown("### 답변 전략별 분포")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(f"**Prompt 직접**: {strategy_counts['prompt_direct']}건")
    with col2:
        st.warning(f"**Tool + RAG**: {strategy_counts['tool_rag']}건")
    with col3:
        st.error(f"**답변 안함**: {strategy_counts['no_response']}건")

    # 레이블별 분포
    st.markdown("### 문의 유형별 분포")

    # 답변 안함
    st.markdown("**🚫 답변 안함 (운영자 에스컬레이션)**")
    cols = st.columns(5)
    i = 0
    for label, count in sorted(label_counts.items()):
        # no_response 전략인지 확인
        if any(categorize_inquiry({'title': '', 'content': label}, [])['strategy'] == 'no_response'
               for _ in [1] if label in ['개인 계정 조치 필요', '플랫폼 시스템 에러', '미분류']):
            with cols[i % 5]:
                st.metric(label, f"{count}건")
                i += 1

    # Prompt 직접
    st.markdown("**✅ Prompt 직접 답변**")
    cols = st.columns(5)
    i = 0
    for label, count in sorted(label_counts.items()):
        if label in ['강의/수강 안내', '과제 제출 규정', '서비스 이용 가이드', '기능 개선/건의', '플랫폼 API 사용법', '강의 영상 재생 오류']:
            with cols[i % 5]:
                st.metric(label, f"{count}건")
                i += 1

    # Tool + RAG
    st.markdown("**🔧 Tool + RAG**")
    cols = st.columns(5)
    i = 0
    for label, count in sorted(label_counts.items()):
        if label in ['과제 개발 방법 문의', '코드 로직 에러']:
            with cols[i % 5]:
                st.metric(label, f"{count}건")
                i += 1

except FileNotFoundError:
    st.warning("데이터 파일을 찾을 수 없습니다. inquiry.json과 inquiry_comment.json이 있는지 확인하세요.")

# 푸터
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>AI Talent Lab 문의하기 Agent PoC - Streamlit 데모</p>
</div>
""", unsafe_allow_html=True)
