"""인수인계 문서 생성 스크립트 — Word(.docx) 형식"""

import os
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()

# ── 스타일 설정 ──
style = doc.styles['Normal']
style.font.name = '맑은 고딕'
style.font.size = Pt(10)
style.paragraph_format.space_after = Pt(4)
style.paragraph_format.line_spacing = 1.35

for level in range(1, 4):
    hs = doc.styles[f'Heading {level}']
    hs.font.name = '맑은 고딕'
    hs.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

# ── 헬퍼 함수 ──
def add_table(headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(9)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[ri + 1].cells[ci]
            cell.text = str(val)
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph()

def add_code(text):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = 'Consolas'
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)

def add_bullet(text, level=0):
    p = doc.add_paragraph(text, style='List Bullet')
    p.paragraph_format.left_indent = Cm(1.0 + level * 0.8)
    for r in p.runs:
        r.font.size = Pt(9.5)


# ════════════════════════════════════════════════════════════════
# 문서 본문 시작
# ════════════════════════════════════════════════════════════════

# 표지
doc.add_paragraph()
doc.add_paragraph()
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run('AI Talent Lab 문의하기 Agent\n인수인계 문서')
run.bold = True
run.font.size = Pt(22)
run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

doc.add_paragraph()
subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run('inquiry_agent.py 기반 자동 응답 시스템\n브랜치: indiv_nolabel')
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

doc.add_paragraph()
date_p = doc.add_paragraph()
date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = date_p.add_run('2026년 4월')
run.font.size = Pt(11)

doc.add_page_break()

# ── 목차 ──
doc.add_heading('목차', level=1)
toc_items = [
    '1. 시스템 개요',
    '2. 파일 구조',
    '3. 데이터 현황',
    '4. 시스템 기동 및 초기화',
    '5. 문의 처리 파이프라인 (전체 흐름)',
    '  5.1 Step 0: 개인화 컨텍스트 조회',
    '  5.2 Step 1: LLM 분류',
    '  5.3 Step 2: Strategy 결정',
    '  5.4 Step 3-A: Tool Action (Group 3)',
    '  5.5 Step 3-B: RAG 검색',
    '  5.6 Step 4: 답변 생성 + LLM 자체 평가',
    '  5.7 Step 5: 2차 다운그레이드',
    '6. 카테고리 라벨 (12개)',
    '7. Knowledge Base (KB) 구조',
    '8. Schedule 구조 (프로그램별 분리)',
    '9. 프롬프트 주입 구조',
    '10. 실행 방법',
    '11. 테스트 방법',
    '12. 기수 전환 시 운영 절차',
    '13. 주요 설정값',
]
for item in toc_items:
    p = doc.add_paragraph(item)
    p.paragraph_format.space_after = Pt(1)
    for r in p.runs:
        r.font.size = Pt(10)

doc.add_page_break()

# ════════════════════════════════════════════════════════════════
# 1. 시스템 개요
# ════════════════════════════════════════════════════════════════
doc.add_heading('1. 시스템 개요', level=1)

doc.add_paragraph(
    'AI Talent Lab 문의하기 게시판에 들어오는 수강생 문의를 자동으로 분류하고, '
    '답변 가능한 문의에는 RAG 기반 답변을 생성하며, 코드 리뷰 횟수 초기화 등의 '
    '운영 작업은 에이전트가 직접 DB를 조작하여 처리하는 시스템입니다.'
)

doc.add_paragraph('핵심 특징:')
add_bullet('LLM 2회 호출: 1회차 분류, 2회차 답변 생성 (Azure gpt-5.2)')
add_bullet('FAISS 벡터 검색 기반 RAG (Azure text-embedding-3-large, 3072차원)')
add_bullet('수강생 개인화: SQLite DB에서 수강 이력·리뷰 횟수 조회 → 프롬프트 주입')
add_bullet('Tool 직접 실행: 코드 리뷰 횟수 초기화, 사전연습 횟수 복구 (DB 조작)')
add_bullet('4단계 전략 분기: tool_action → no_response → human_review → tool_rag')
add_bullet('배치 평가 모드 + 대화형(Interactive) 모드 지원')

# ════════════════════════════════════════════════════════════════
# 2. 파일 구조
# ════════════════════════════════════════════════════════════════
doc.add_heading('2. 파일 구조', level=1)

add_table(
    ['파일/폴더', '설명'],
    [
        ['inquiry_agent.py', '메인 Agent (분류·RAG·답변·strategy 결정, 대화형 모드 포함)'],
        ['user_db.py', '수강생 개인화 DB (SQLite) + Tool용 리뷰/연습 횟수 관리'],
        ['tools.py', 'Group 3 Tool 정의 및 실행기 (AUTO_TOOL / APPROVAL_TOOL)'],
        ['reset_test_data.py', 'Tool 테스트용 DB 더미 데이터 유틸리티'],
        ['info/kb/knowledge_base.json', '사전 지식 + 큐레이션 Q&A + 에러 솔루션 (현재 v2.0.0)'],
        ['info/schedule/bootcamp.json', 'AI Bootcamp 일정 (현재 14기(8차))'],
        ['info/schedule/literacy.json', 'AI Literacy 인증시험 일정 (현재 14차)'],
        ['info/schedule/master_project.json', 'AI Master Project 일정 (현재 5기)'],
        ['info/past/', '과거 버전 보관 (파일명에 유효 종료일 _~YYYYMMDD 표기)'],
        ['info/inquiry_all.json', '전체 문의 게시물 (315건)'],
        ['info/inquiry_comment_all.json', '전체 문의 댓글 (344건, admin 289건)'],
        ['tests/', '테스트셋 JSON 및 평가 결과 (eval_result_*.json)'],
        ['embeddings_cache.pkl', '임베딩 캐시 (재실행 시 API 미호출)'],
        ['user_data.db', 'SQLite DB (수강생·코드리뷰·연습 횟수)'],
        ['pipeline_viz.html', '파이프라인 시각화 (브라우저에서 열기)'],
    ],
    col_widths=[5.5, 11.5],
)

# ════════════════════════════════════════════════════════════════
# 3. 데이터 현황
# ════════════════════════════════════════════════════════════════
doc.add_heading('3. 데이터 현황', level=1)

doc.add_paragraph('2026-04-14 기준 데이터:')
add_table(
    ['구분', '건수', '비고'],
    [
        ['전체 문의', '315건', 'inquiry_all.json (2025-12-14 ~ 2026-04-14)'],
        ['전체 댓글', '344건', 'inquiry_comment_all.json'],
        ['관리자 답변', '289건 (274 문의)', 'author_id in ADMIN_IDS OR is_admin=1'],
        ['RAG pool (학습용)', '~270건', '테스트 제외, admin 답변 있는 것만'],
        ['KB 큐레이션 Q&A', '47건', 'knowledge_base.json v2.0 label_examples'],
        ['에러 솔루션', '15건', 'knowledge_base.json v2.0 error_solutions'],
        ['important_facts', '36개', 'knowledge_base.json v2.0 prior_knowledge'],
    ],
    col_widths=[4, 3.5, 9.5],
)

doc.add_paragraph('관리자 답변 필터 (신·구 포맷 호환):')
add_bullet('구 형식: author_id in {2, 7, 61, 442, 2425, 3417}')
add_bullet('신 형식 (2026-03 이후): author_id=null, is_admin=1')
add_bullet('코드에서 OR 조건으로 양쪽 모두 처리')

# ════════════════════════════════════════════════════════════════
# 4. 시스템 기동 및 초기화
# ════════════════════════════════════════════════════════════════
doc.add_heading('4. 시스템 기동 및 초기화', level=1)

doc.add_paragraph('InquiryAgent() 생성 시 초기화 순서:')

add_table(
    ['순서', '대상', '소스', '설명'],
    [
        ['1', 'KB 로드', 'info/kb/knowledge_base.json', 'prior_knowledge, label_examples, error_solutions'],
        ['2', 'Schedule 로드', 'info/schedule/*.json', 'bootcamp, literacy, master_project 파일을 자동 스캔하여 dict 합성'],
        ['3', 'UserContextDB', 'user_data.db (SQLite)', 'users, cohorts, enrollments, code_review_logs, practice_sessions'],
        ['4', 'LLM 클라이언트', 'Azure OpenAI', 'gpt-5.2 (분류+답변), text-embedding-3-large (벡터 검색)'],
        ['5', 'FAISS 인덱스', 'KB + inquiry_all.json', 'load_inquiry_history() 호출 시 벡터 인덱스 구축 (~330건)'],
    ],
    col_widths=[1.5, 3, 5, 7.5],
)

doc.add_paragraph('Schedule 로드 방식:')
add_bullet('_load_schedule()가 info/schedule/ 폴더의 모든 .json 파일을 순회')
add_bullet('파일명(확장자 제거)이 dict key가 됨: bootcamp.json → schedule["bootcamp"]')
add_bullet('기수 전환 시 해당 파일만 교체하면 됨 (코드 수정 불필요)')

doc.add_paragraph('FAISS 인덱스 구성:')
add_table(
    ['출처', '문서 수', '설명'],
    [
        ['KB 큐레이션 Q&A', '47건', 'label_examples의 qa_examples (제목+질문 텍스트 임베딩)'],
        ['에러 솔루션', '15건', 'error_solutions (제목+솔루션 텍스트 임베딩)'],
        ['History', '~270건', 'inquiry_all.json 중 admin 답변 보유 문의 (제목+본문 임베딩)'],
    ],
    col_widths=[4, 2.5, 10.5],
)
add_bullet('임베딩 모델: Azure text-embedding-3-large (3072차원)')
add_bullet('인덱스: FAISS IndexFlatIP (코사인 유사도, L2 정규화 후 inner product)')
add_bullet('캐시: embeddings_cache.pkl — 한번 임베딩하면 재실행 시 API 미호출')

# ════════════════════════════════════════════════════════════════
# 5. 문의 처리 파이프라인
# ════════════════════════════════════════════════════════════════
doc.add_heading('5. 문의 처리 파이프라인 (전체 흐름)', level=1)

doc.add_paragraph(
    '문의 1건이 process_inquiry()에 들어오면 아래 단계를 순차 실행합니다. '
    'LLM은 총 2회 호출됩니다 (분류 1회 + 답변 생성 1회). '
    'tool_action 경로는 LLM 1회(분류)만 호출하고 답변은 코드가 직접 생성합니다.'
)

# Step 0
doc.add_heading('5.1 Step 0: 개인화 컨텍스트 조회', level=2)
doc.add_paragraph(
    'author_id를 기반으로 user_db.py의 build_personal_context_str()을 호출하여 '
    '해당 수강생의 수강 이력, 코드 리뷰 사용 현황, AI Literacy 연습 횟수를 조회합니다. '
    '조회된 텍스트는 이후 분류·답변 프롬프트 양쪽에 주입됩니다.'
)

# Step 1
doc.add_heading('5.2 Step 1: LLM 분류 (_llm_classify)', level=2)
doc.add_paragraph('LLM(gpt-5.2)에게 system prompt + 문의 텍스트를 보내서 분류를 요청합니다.')

doc.add_paragraph('System prompt 구성:')
add_bullet('개인 컨텍스트 (Step 0에서 조회한 수강 이력)')
add_bullet('_prior_knowledge_section(): KB의 prior_knowledge → 마크다운 텍스트로 변환')
add_bullet('_schedule_section(): schedule/*.json 3개 파일 합성 → 마크다운 텍스트로 변환')
add_bullet('_label_description_section(): 12개 라벨별 description + typical_patterns + qa_examples 제목')
add_bullet('분류 판단 기준: 혼동 쌍 구분, 신뢰도 판단 요소, 복합 문의 감지 규칙')

doc.add_paragraph('LLM 출력 (JSON):')
add_bullet('label: 12개 카테고리 중 하나')
add_bullet('confidence_level: high / low')
add_bullet('is_compound: 복합 문의 여부')
add_bullet('sub_labels: 감지된 모든 라벨 목록')
add_bullet('rationale: 분류 근거')

# Step 2
doc.add_heading('5.3 Step 2: Strategy 결정 (_determine_strategy)', level=2)
doc.add_paragraph('Python 코드 로직으로 처리 전략을 결정합니다 (LLM 호출 아님). 우선순위 순:')

add_table(
    ['우선순위', '조건', '전략', '설명'],
    [
        ['1', '복합 문의 + Group1 포함', 'human_review', '운영자 직접 조치 필요한 건 포함'],
        ['2', '복합 문의 + Group2만 4개+', 'human_review', '복잡도 초과'],
        ['3', '복합 문의 + Group2만 2~3개', 'tool_rag', 'sub_label별 각각 RAG 후 context 합산'],
        ['4', 'Group 3 라벨', 'tool_action', '에이전트가 DB 직접 조작 (즉시 처리)'],
        ['5', 'Group 1 OR confidence==low', 'no_response', '운영자 에스컬레이션 (답변 없음)'],
        ['6', 'confidence==high (Group 2)', 'tool_rag', 'RAG 검색 후 답변 생성 시도'],
    ],
    col_widths=[2, 5, 3, 7],
)

# Step 3-A
doc.add_heading('5.4 Step 3-A: Tool Action (Group 3 경로)', level=2)
doc.add_paragraph('tools.py의 execute_tool_action()이 실행됩니다. RAG를 거치지 않고 즉시 DB 조작 후 답변을 반환합니다.')

add_table(
    ['라벨', 'Tool 종류', 'DB 작업', '답변 예시'],
    [
        ['CODE_REVIEW_RESET', 'AUTO_TOOL',
         'code_review_logs 테이블에서\n당일 used_count = 0 초기화\nreset_count 1 증가',
         '코드 리뷰 횟수를 초기화했습니다.\n오늘 다시 10회 요청하실 수 있습니다.'],
        ['LITERACY_PRACTICE_RESET', 'AUTO_TOOL',
         'practice_sessions 테이블에서\ntutorial_attempts 증가 (복구)\n문의에서 횟수 추출 (기본 1회)',
         'AI Literacy 사전연습 횟수 1회를\n복구했습니다.'],
    ],
    col_widths=[4.5, 2.5, 5, 5],
)

# Step 3-B
doc.add_heading('5.5 Step 3-B: RAG 검색 (_build_kb_context)', level=2)
doc.add_paragraph('tool_rag 또는 human_review 경로에서 실행됩니다.')

doc.add_paragraph('검색 방식 (similarity_only=True):')
add_bullet('① FAISS 벡터 검색: 라벨 무시, 순수 코사인 유사도 상위 5개 문서 반환')
add_bullet('② 에러 솔루션 regex 보완: CODE_LOGIC_ERROR이거나 에러 키워드 감지 시 error_solutions의 정규식 매칭')
add_bullet('③ 과정 정보 보완: COURSE_INFO 라벨일 때 prior_knowledge.programs 키워드 매칭')

doc.add_paragraph('1차 다운그레이드 (RAG 유사도 기반):')
add_bullet('max_score < 0.65 → tool_rag을 human_review로 다운그레이드')

doc.add_paragraph('복합 문의 (Group2 2~3개):')
add_bullet('sub_label 각각 RAG 검색 → context 합산')
add_bullet('min(scores) < 0.65 → human_review 다운그레이드')

# Step 4
doc.add_heading('5.6 Step 4: 답변 생성 + LLM 자체 평가 (_generate_answer)', level=2)
doc.add_paragraph('LLM(gpt-5.2) 2번째 호출. RAG 검색 결과를 참고 정보로 넘깁니다.')

doc.add_paragraph('System prompt 구성:')
add_bullet('개인 컨텍스트 + prior_knowledge + schedule (분류와 동일)')
add_bullet('답변 규칙: 언어 감지, 인사말, "추측 금지", "내부 용어 노출 금지"')
add_bullet('답변 신뢰도 자체 평가 기준 (high / medium / low)')

doc.add_paragraph('User prompt 구성:')
add_bullet('[문의] 제목 + 내용')
add_bullet('[참고 정보] RAG 검색 결과 context (유사 Q&A + 에러 솔루션)')

doc.add_paragraph('LLM 출력:')
add_bullet('answer: 답변 텍스트')
add_bullet('answer_confidence: high / medium / low')
add_bullet('uncertain_parts: 확신 없는 부분 설명')

# Step 5
doc.add_heading('5.7 Step 5: 2차 다운그레이드', level=2)
doc.add_paragraph('답변 신뢰도를 기반으로 최종 전략을 결정합니다 (다운그레이드만, 업그레이드 없음):')

add_table(
    ['answer_confidence', '처리', '설명'],
    [
        ['low', 'no_response', 'KB 근거 부족 → 에스컬레이션 (답변 버림)'],
        ['medium', 'human_review', '답변 앞에 [초안] 태그 부착, 운영자 검토'],
        ['high', '기존 strategy 유지', 'tool_rag이면 자동 게시'],
    ],
    col_widths=[3.5, 4, 9.5],
)

# ════════════════════════════════════════════════════════════════
# 6. 카테고리 라벨
# ════════════════════════════════════════════════════════════════
doc.add_heading('6. 카테고리 라벨 (12개)', level=1)

doc.add_heading('Group 1 — no_response (운영자 에스컬레이션, 5개)', level=2)
add_table(
    ['라벨', '설명'],
    [
        ['ACCOUNT_ACTION_REQUIRED', '개인 계정·권한·인증 직접 조치 필요'],
        ['PLATFORM_SYSTEM_ERROR', '플랫폼 서버·시스템 에러'],
        ['VIDEO_PLAYBACK_ERROR', '강의 영상 재생 안됨'],
        ['FEATURE_REQUEST', '기능 개선·건의'],
        ['UNCATEGORIZED', '내용 불명확·분류 불가'],
    ],
    col_widths=[5.5, 11.5],
)

doc.add_heading('Group 2 — tool_rag (RAG 기반 답변, 5개)', level=2)
add_table(
    ['라벨', '설명'],
    [
        ['COURSE_INFO', '강의 목록·수강 방법·커리큘럼·수료 조건'],
        ['SUBMISSION_POLICY', '과제 제출 횟수·마감·재제출·평가 결과 발표'],
        ['SERVICE_GUIDE', '플랫폼 이용 방법·가이드'],
        ['ASSIGNMENT_DEVELOPMENT', '과제 구현 방법·개발 방향·아키텍처'],
        ['CODE_LOGIC_ERROR', '코드 에러·API 호출·환경 오류'],
    ],
    col_widths=[5.5, 11.5],
)

doc.add_heading('Group 3 — tool_action (에이전트 직접 실행, 2개)', level=2)
add_table(
    ['라벨', '설명', 'DB 작업'],
    [
        ['CODE_REVIEW_RESET', '코드 리뷰 횟수 초기화 요청', 'code_review_logs.used_count = 0'],
        ['LITERACY_PRACTICE_RESET', 'AI Literacy 사전연습 횟수 복구', 'practice_sessions.tutorial_attempts 증가'],
    ],
    col_widths=[5, 6, 6],
)

# ════════════════════════════════════════════════════════════════
# 7. KB 구조
# ════════════════════════════════════════════════════════════════
doc.add_heading('7. Knowledge Base (KB) 구조', level=1)

doc.add_paragraph('파일: info/kb/knowledge_base.json (현재 v2.0.0, 2026-04-16 갱신)')

add_table(
    ['섹션', '내용', '프롬프트 사용처'],
    [
        ['prior_knowledge', '플랫폼 소개, 교육 과정 설명, important_facts 36개', '분류 + 답변 system prompt 양쪽'],
        ['label_examples', '12개 라벨별 description, typical_patterns, qa_examples 47건', '분류 system prompt (라벨 설명)\nRAG 검색 소스 (FAISS 인덱스)'],
        ['error_solutions', '15개 에러 패턴 정규식 + 솔루션', 'RAG 검색 시 regex 보완\nFAISS 인덱스 소스'],
    ],
    col_widths=[3.5, 7, 6.5],
)

doc.add_paragraph('과거 버전 보관: info/past/knowledge_base_v1_~20260403.json')

# ════════════════════════════════════════════════════════════════
# 8. Schedule 구조
# ════════════════════════════════════════════════════════════════
doc.add_heading('8. Schedule 구조 (프로그램별 분리)', level=1)

doc.add_paragraph('info/schedule/ 폴더에 프로그램별 JSON 파일로 분리 관리합니다.')

add_table(
    ['파일', '현재 내용', '교체 주기'],
    [
        ['bootcamp.json', '14기(8차), 2026-04-20~05-15, 예정 9차~14차', '~4주마다 (기수 전환 시)'],
        ['literacy.json', '인증시험 14차, 시험일 2026-04-28', '시험 차수 변경 시'],
        ['master_project.json', '5기, 2026-04-06~05-29, 예정 6~8기', '~8주마다'],
    ],
    col_widths=[4.5, 7.5, 5],
)

doc.add_paragraph('로드 방식:')
add_bullet('_load_schedule()가 info/schedule/ 폴더의 .json 파일을 자동 스캔')
add_bullet('파일명(확장자 제거)이 dict key: bootcamp.json → schedule["bootcamp"]')
add_bullet('_schedule_section()이 dict를 마크다운 텍스트로 변환하여 LLM 프롬프트에 주입')

# ════════════════════════════════════════════════════════════════
# 9. 프롬프트 주입 구조
# ════════════════════════════════════════════════════════════════
doc.add_heading('9. 프롬프트 주입 구조', level=1)

doc.add_paragraph('JSON 파일은 LLM에 직접 전달되지 않습니다. Python 코드가 마크다운 텍스트로 변환한 뒤 system prompt에 주입합니다.')

doc.add_heading('분류 프롬프트 (_llm_classify)', level=2)
add_table(
    ['위치', '내용', '소스'],
    [
        ['system prompt', '개인 컨텍스트', 'user_db.py'],
        ['system prompt', 'prior_knowledge (플랫폼 사전 지식)', 'KB prior_knowledge'],
        ['system prompt', 'schedule (운영 일정)', 'schedule/*.json'],
        ['system prompt', '12개 라벨 정의 + 예시 제목', 'KB label_examples'],
        ['system prompt', '혼동 쌍 구분 기준', '코드 내 하드코딩'],
        ['user prompt', '문의 제목 + 내용', '입력 문의'],
    ],
    col_widths=[3, 6, 8],
)

doc.add_heading('답변 프롬프트 (_generate_answer)', level=2)
add_table(
    ['위치', '내용', '소스'],
    [
        ['system prompt', '개인 컨텍스트', 'user_db.py'],
        ['system prompt', 'prior_knowledge', 'KB prior_knowledge'],
        ['system prompt', 'schedule', 'schedule/*.json'],
        ['system prompt', '답변 규칙 + 신뢰도 평가 기준', '코드 내 하드코딩'],
        ['user prompt', '문의 제목 + 내용', '입력 문의'],
        ['user prompt', '[참고 정보] RAG 검색 결과', 'FAISS 검색 + error regex + 과정 정보'],
    ],
    col_widths=[3, 6, 8],
)

# ════════════════════════════════════════════════════════════════
# 10. 실행 방법
# ════════════════════════════════════════════════════════════════
doc.add_heading('10. 실행 방법', level=1)

doc.add_heading('환경 준비', level=2)
add_code('pip install openai faiss-cpu==1.7.4 "numpy<2"')
doc.add_paragraph('.env 파일에 Azure OpenAI 키 설정 필요:')
add_code('AZURE_OPENAI_API_KEY=<key>\nAZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/\nAZURE_CHAT_DEPLOYMENT=gpt-5.2\nAZURE_OPENAI_EMBED_API_KEY=<key>\nAZURE_OPENAI_EMBED_ENDPOINT=https://<resource>.openai.azure.com/\nAZURE_EMBED_DEPLOYMENT=text-embedding-3-large')

doc.add_heading('배치 평가 모드', level=2)
add_code('python inquiry_agent.py                                   # inquiry_all.json에서 random 샘플링')
add_code('python inquiry_agent.py --n-test 20 --random-state 12     # 샘플 수·시드 지정')
add_code('python inquiry_agent.py --test-file tests/test_set_50.json # 외부 테스트셋 평가')

doc.add_heading('대화형 모드', level=2)
add_code('python inquiry_agent.py --interactive --author-id 277')
doc.add_paragraph("'>>>' 프롬프트에 문의 입력 → 분류 → 전략 → 답변/Tool 실행 결과 출력. exit/quit/빈 입력으로 종료.")

doc.add_heading('대화형 모드 실행 예시', level=2)
doc.add_paragraph('아래는 author_id=277 수강생으로 대화형 모드를 실행한 실제 로그입니다. 기동 → DB 컨텍스트 출력 → 다양한 유형의 문의 처리까지의 전체 흐름을 보여줍니다.')

doc.add_paragraph('[기동 로그]', style='Normal')
add_code(
    'PS> python inquiry_agent.py --interactive --author-id 277\n'
    '[KB] v2.0.0  [Schedule] [\'bootcamp\', \'literacy\', \'master_project\']\n'
    '[타이머] Agent 초기화: 0.3s\n'
    '[타이머] JSON 로드: 0.0s\n'
    '통합 문의 데이터: 315건 / 댓글: 344건\n'
    'RAG pool: 274건 (admin 답변 보유 문의 전체)\n'
    '벡터 인덱스 구축 중... (총 336개 문서)\n'
    '  faiss 로딩 중... 완료 (0.4s)\n'
    '  임베딩 캐시 100% 히트 (336건)\n'
    '  FAISS 인덱스 구축 완료: 336개 벡터\n'
    '[타이머] RAG history 로드 + 벡터 인덱스: 0.6s\n'
    'Agent 준비 완료'
)

doc.add_paragraph('[수강생 DB 컨텍스트 자동 출력]', style='Normal')
add_code(
    '============================================================\n'
    '대화형 모드  author_id=277\n'
    '============================================================\n'
    '[DB] ## 문의자 수강 이력\n'
    '[DB] - 현재 과정: AI Bootcamp 12기 (진행중) — 재수강 (10기 미수료 이력 있음)\n'
    '[DB] - 전체 이력:\n'
    '[DB]   · AI Bootcamp 10기: 미수료 (점수: 38.0) — 최종과제 미제출로 미수료\n'
    '[DB]   · AI Bootcamp 12기: 진행중 — 재수강\n'
    '\'exit\' / \'quit\' / 빈 입력 → 종료'
)

doc.add_paragraph('예시 ①: 답변 불가 문의 → 운영자 에스컬레이션 (no_response)')
doc.add_paragraph(
    '수강생의 코드 리뷰 잔여 횟수는 개인별 실시간 데이터로, 텍스트만으로는 분류도 답변도 불가하여 '
    '운영자에게 에스컬레이션됩니다.'
)
add_code(
    '>>> 지금 코드 리뷰횟수 얼마남았어?\n'
    '\n'
    '[Label]    UNCATEGORIZED\n'
    '[Strategy] 운영자 에스컬레이션\n'
    '\n'
    '(답변 없음 — 코드 리뷰 잔여 횟수는 사용자별 데이터 확인이 필요해\n'
    '텍스트만으로 분류·답변이 불가함)'
)

doc.add_paragraph('예시 ②: Tool 직접 실행 — AI Literacy 사전연습 횟수 복구 (tool_action)')
doc.add_paragraph(
    'LITERACY_PRACTICE_RESET으로 분류되어 에이전트가 직접 DB를 조작하고 결과를 즉시 반환합니다.'
)
add_code(
    '>>> 연습시험횟수 초기화 해줘\n'
    '\n'
    '[Label]    LITERACY_PRACTICE_RESET\n'
    '[Strategy] 에이전트 직접 실행\n'
    '[Tool]     성공\n'
    '  → 복구 1회 / 남은 100회 (literacy_test_id=None)\n'
    '\n'
    '안녕하세요, AI Talent Lab입니다.\n'
    'AI Literacy 사전연습 횟수 1회를 복구했습니다. 다시 연습하실 수 있습니다.\n'
    '\n'
    '감사합니다.'
)

doc.add_paragraph('예시 ③: 상세한 상황 설명 → Tool 직접 실행')
doc.add_paragraph(
    '문의 내용이 길어도 핵심(사전연습 횟수 복구 요청)을 정확히 판별하여 같은 Tool을 실행합니다.'
)
add_code(
    '>>> 사전연습 첫번째 문제를 진행하는 과정에서 브라우저 오류로 임시 저장 및\n'
    '    저장하기 등이 진행이 되지 않고 오류가 발생하여 카운트가 소진되어\n'
    '    정상화 가능할지 문의드립니다. 감사합니다.\n'
    '\n'
    '[Label]    LITERACY_PRACTICE_RESET\n'
    '[Strategy] 에이전트 직접 실행\n'
    '[Tool]     성공\n'
    '  → 복구 0회 / 남은 100회 (literacy_test_id=None)\n'
    '\n'
    '안녕하세요, AI Talent Lab입니다.\n'
    'AI Literacy 사전연습 횟수 0회를 복구했습니다. 다시 연습하실 수 있습니다.\n'
    '\n'
    '감사합니다.'
)

doc.add_paragraph('예시 ④: 복잡한 환경 문의 → RAG 초안 + 운영자 검토 (human_review)')
doc.add_paragraph(
    '보안정책상 파일 업로드가 불가한 특수 상황. RAG로 유사 사례를 찾아 초안을 생성하지만, '
    '확실하지 않은 부분이 있어 운영자 검토가 필요한 [초안]으로 분류됩니다.'
)
add_code(
    '>>> 안녕하세요 ict서비스팀 김승동 매니저입니다. 제고객사 보안솔루션이 설치된\n'
    '    로컬 환경에서 과제를 작성했는데, 고객사 보안정책상 이미지, 소스 등이\n'
    '    업로드가 불가합니다. 하여 프로젝트 파일 및 이미지 등은 SKAX VDI로\n'
    '    올려놨으나 당사도 정책상 외부 메일로 해당 파일들 송부가 되지 않습니다.\n'
    '    당 파일을 업로드 할 방법이 현재로서는 없는 관계로 다른 방법이 있을지\n'
    '    문의드립니다.\n'
    '\n'
    '[Label]    SERVICE_GUIDE\n'
    '[Strategy] RAG 초안 + 운영자 검토\n'
    '\n'
    '[초안] 안녕하세요, AI Talent Lab입니다.\n'
    '\n'
    '문의 주신 상황에서는 웹 IDE 환경에서 직접 개발/정리하여 제출하시는 것을\n'
    '권장드립니다.\n'
    '\n'
    '1) 웹 IDE 환경에서 직접 개발\n'
    '   - AI Bootcamp 과제는 플랫폼 내 웹 IDE 개발환경에서 바로 개발 및\n'
    '     실행이 가능합니다.\n'
    '\n'
    '2) 업로드가 가능한 환경에서 zip 파일 업로드 후 압축 해제\n'
    '   - 소스 폴더를 zip으로 압축하여 \'최종과제 > 서비스 개발\' 화면에\n'
    '     업로드 후 Terminal에서 unzip 하실 수 있습니다.\n'
    '\n'
    '감사합니다.'
)

doc.add_paragraph('예시 ⑤: API 호출 지연 문의 → RAG 초안 (CODE_LOGIC_ERROR)')
add_code(
    '>>> 과제 올려서 stremlit 으로 실행을 시켜보고 있는데, Azure OpenAI API\n'
    '    호출 후 시간이 지나도 결과를 못 받고 있습니다. 뭔가 제한이 걸려있는걸까요?\n'
    '\n'
    '[Label]    CODE_LOGIC_ERROR\n'
    '[Strategy] RAG 초안 + 운영자 검토\n'
    '\n'
    '[초안] 안녕하세요, AI Talent Lab입니다.\n'
    '\n'
    'Streamlit에서 Azure OpenAI 호출 후 응답이 오지 않는 경우,\n'
    '(1) 일시적 사용량 증가로 인한 지연/타임아웃\n'
    '(2) timeout 미설정\n'
    '(3) 환경변수/엔드포인트 오참조에 주로 발생합니다.\n'
    '\n'
    '플랫폼 환경에서는 os.getenv("AOAI_API_KEY"),\n'
    'os.getenv("AOAI_ENDPOINT")로 읽어 사용 중인지 확인해주세요.\n'
    '\n'
    '감사합니다.'
)

doc.add_paragraph('예시 ⑥: 플랫폼 장애 → 운영자 에스컬레이션 (no_response)')
doc.add_paragraph(
    'PLATFORM_SYSTEM_ERROR(Group 1)로 분류되어 답변 없이 운영자에게 에스컬레이션됩니다.'
)
add_code(
    '>>> 부캠 과제 제출 Console 에서 세션 생성 실패 문구가 반복되고 있습니다.\n'
    '    조치 방법을 알 수 있을까요?\n'
    '\n'
    '[Label]    PLATFORM_SYSTEM_ERROR\n'
    '[Strategy] 운영자 에스컬레이션\n'
    '\n'
    '(답변 없음 — Bootcamp 과제 제출 콘솔에서 \'세션 생성 실패\'가 반복되는 것은\n'
    '코드 문제가 아닌 플랫폼 콘솔/세션 접속 장애로 보임)'
)

doc.add_paragraph()
doc.add_paragraph(
    '위 예시에서 볼 수 있듯이, 같은 대화형 세션에서 다양한 유형의 문의가 들어와도 '
    '각각 적절한 경로(tool_action / human_review / no_response)로 처리됩니다. '
    'DB 컨텍스트(수강 이력)는 세션 시작 시 한 번 로드되어 모든 문의에 공통 적용됩니다.'
)

# ════════════════════════════════════════════════════════════════
# 11. 테스트 방법
# ════════════════════════════════════════════════════════════════
doc.add_heading('11. 테스트 방법', level=1)

doc.add_heading('테스트셋', level=2)
add_table(
    ['파일', '건수', '용도'],
    [
        ['tests/test_set_1.json', '1건', '단건 빠른 검증 (파이프라인 전체 동작 확인)'],
        ['tests/test_personalized.json', '12건', '개인화 DB 테스트 (실제 DB의 author_id 사용)'],
        ['tests/test_set_50.json', '50건', '정량 평가 (30건 수작업 기대 예시 + 20건 inquiry_all 추출)'],
    ],
    col_widths=[5.5, 2, 9.5],
)

doc.add_heading('평가 결과', level=2)
doc.add_paragraph('실행 시 tests/eval_result_YYYYMMDD_HHMMSS.json이 자동 생성됩니다. 포함 내용:')
add_bullet('eval_info: 테스트 파일, 케이스 수, RAG pool 크기')
add_bullet('summary: 전략별 건수 집계, 복합 문의 수')
add_bullet('results: 건별 label, confidence, strategy, answer, actual_answer(비교용)')

doc.add_heading('Tool 테스트 (reset_test_data.py)', level=2)
add_code('python reset_test_data.py                     # 더미 데이터 초기화')
add_code('python reset_test_data.py --show              # 현재 DB 상태 조회')
add_code('python reset_test_data.py --use-review 277 10 # user 277 리뷰 10회 사용 (소진 상태)')
add_code('python reset_test_data.py --use-practice 277 100  # user 277 연습 전부 소진')
doc.add_paragraph('소진 상태를 만든 뒤 대화형 모드에서 "코드 리뷰 초기화 해주세요" 등을 테스트합니다.')

# ════════════════════════════════════════════════════════════════
# 12. 기수 전환 시 운영 절차
# ════════════════════════════════════════════════════════════════
doc.add_heading('12. 기수 전환 시 운영 절차', level=1)

doc.add_paragraph('예시: Bootcamp 14기(8차) → 15기(9차) 전환')

doc.add_paragraph('1. 현재 파일 아카이브:')
add_code('info/schedule/bootcamp.json → info/past/bootcamp_14기_~20260515.json')

doc.add_paragraph('2. bootcamp.json 갱신:')
add_bullet('current_cohort를 "15기 (9차)"로 변경')
add_bullet('enrollment_period, course_period, assignment_deadline, result_announcement 업데이트')
add_bullet('upcoming_cohorts에서 해당 기수 제거')

doc.add_paragraph('3. KB 갱신 (필요 시):')
add_bullet('새로운 문의 패턴이 발견되면 info/kb/knowledge_base.json의 qa_examples 추가')
add_bullet('이전 KB를 info/past/knowledge_base_v2_~YYYYMMDD.json으로 아카이브')
add_bullet('version, last_updated 필드 업데이트')

doc.add_paragraph('4. 데이터 갱신 (필요 시):')
add_bullet('새 문의 데이터를 inquiry_all.json, inquiry_comment_all.json에 병합')
add_bullet('embeddings_cache.pkl 삭제 → 다음 실행 시 자동 재구축')

doc.add_paragraph('코드 수정은 불필요합니다. 파일만 교체하면 됩니다.')

# ════════════════════════════════════════════════════════════════
# 13. 주요 설정값
# ════════════════════════════════════════════════════════════════
doc.add_heading('13. 주요 설정값', level=1)

add_table(
    ['설정', '값', '위치', '설명'],
    [
        ['RAG_CONFIDENCE_THRESHOLD', '0.65', 'inquiry_agent.py', 'RAG 유사도 임계값. 미만이면 human_review'],
        ['CODE_REVIEW_DAILY_LIMIT', '10', 'user_db.py', '코드 리뷰 일일 한도'],
        ['PRACTICE_DEFAULT_RESTORE', '1', 'tools.py', '사전연습 기본 복구 횟수'],
        ['EMBED_DIM', '3072', 'inquiry_agent.py', 'text-embedding-3-large 벡터 차원'],
        ['top_k', '5', 'inquiry_agent.py', 'FAISS 검색 반환 문서 수'],
        ['ADMIN_IDS', '{2,7,61,442,2425,3417}', 'inquiry_agent.py', '관리자 ID 목록 (구 포맷)'],
    ],
    col_widths=[4.5, 2.5, 4, 6],
)

# ── 저장 ──
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'AI_Talent_Lab_문의Agent_인수인계문서_v2.docx')
doc.save(out_path)
print(f'문서 생성 완료: {out_path}')
