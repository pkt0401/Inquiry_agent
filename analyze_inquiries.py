"""
AI Talent Lab 문의하기 데이터 분석 스크립트

목적:
1. 답변 가능한 질문과 불가능한 질문 분류
2. 특정 context가 필요한 질문 파악
3. 과거 응답 기반 일관성 검토
"""

import json
import csv
import re
from html import unescape
from html.parser import HTMLParser
from datetime import datetime

class MLStripper(HTMLParser):
    """HTML 태그 제거를 위한 파서"""
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
    """HTML 태그 제거 및 텍스트 추출"""
    s = MLStripper()
    s.feed(html)
    return s.get_data().strip()

def categorize_inquiry_type(title, content):
    """문의 유형 분류"""
    text = (title + " " + content).lower()

    # 키워드 기반 분류
    if any(keyword in text for keyword in ['인증', '시험', '버튼', '비활성화', '활성화']):
        return '계정/권한'
    elif any(keyword in text for keyword in ['에러', 'error', '오류', '실행 안', '작동 안']):
        return '기술지원/에러'
    elif any(keyword in text for keyword in ['강의', '과제', '제출', '코드', '실습']):
        return '학습/과제'
    elif any(keyword in text for keyword in ['건의', '개선', '요청', '제안']):
        return '건의/개선'
    else:
        return '기타'

def analyze_answerability(inquiry, comments):
    """
    답변 가능성 분석

    기준:
    - 답변 가능: 운영자가 이미 답변한 경우, 명확한 문제 설명
    - 답변 불가능: 정보 부족, 개인 계정 확인 필요, 시스템 관리자 조치 필요
    - 조건부 답변 가능: 추가 정보 필요
    """
    title = inquiry.get('title', '')
    content = strip_html_tags(inquiry.get('content', ''))
    has_admin_response = any(c.get('is_admin') == 1 for c in comments)

    # 이미 운영자가 답변한 경우
    if has_admin_response:
        admin_response = strip_html_tags(next(c.get('content', '') for c in comments if c.get('is_admin') == 1))

        # 단순 조치 완료 답변
        if '조치' in admin_response and len(admin_response) < 50:
            return {
                'answerability': '답변 불가능',
                'reason': '개인 계정/시스템 조치 필요 (운영자 직접 처리)',
                'confidence': '높음'
            }
        # 명확한 설명이 있는 답변
        elif len(admin_response) > 50:
            return {
                'answerability': '답변 가능',
                'reason': '유사 사례 존재, 명확한 가이드라인 제공 가능',
                'confidence': '높음'
            }

    # 계정 권한 관련
    if categorize_inquiry_type(title, content) == '계정/권한':
        return {
            'answerability': '답변 불가능',
            'reason': '개인 계정 확인 및 시스템 조치 필요',
            'confidence': '높음'
        }

    # 에러 관련
    if categorize_inquiry_type(title, content) == '기술지원/에러':
        # 에러 메시지가 포함되어 있는지 확인
        if 'error' in content.lower() or '에러' in content or len(content) > 200:
            return {
                'answerability': '조건부 답변 가능',
                'reason': '일반적인 에러 해결 가이드 제공 가능, 단 개인 환경 확인 필요할 수 있음',
                'confidence': '중간'
            }
        else:
            return {
                'answerability': '답변 불가능',
                'reason': '구체적인 에러 정보 부족, 추가 정보 필요',
                'confidence': '중간'
            }

    # 학습/과제 관련
    if categorize_inquiry_type(title, content) == '학습/과제':
        return {
            'answerability': '답변 가능',
            'reason': 'FAQ 또는 가이드 문서 기반 답변 가능',
            'confidence': '높음'
        }

    return {
        'answerability': '조건부 답변 가능',
        'reason': '문의 내용에 따라 판단 필요',
        'confidence': '낮음'
    }

def identify_required_context(inquiry, inquiry_type, answerability_info):
    """필요한 context 식별"""
    contexts = []

    # 기본적으로 필요한 context
    contexts.append('FAQ 데이터베이스')
    contexts.append('과거 문의 답변 히스토리')

    # 유형별 필요 context
    if inquiry_type == '계정/권한':
        contexts.extend([
            '사용자 계정 정보 (권한, 그룹, 인증 대상 여부)',
            '인증 시험 일정 및 대상자 정보',
            '사용자별 활성화된 기능 목록'
        ])

    elif inquiry_type == '기술지원/에러':
        contexts.extend([
            '시스템 에러 로그',
            '일반적인 에러 해결 가이드',
            '환경 설정 정보 (Python 버전, 라이브러리 버전 등)',
            'API 키 설정 가이드'
        ])

    elif inquiry_type == '학습/과제':
        contexts.extend([
            '강의 커리큘럼 정보',
            '과제 제출 규정 및 가이드',
            '코드 예제 및 샘플',
            '학습 자료 링크'
        ])

    elif inquiry_type == '건의/개선':
        contexts.extend([
            '현재 서비스 기능 명세',
            '개선 요청 이력',
            '로드맵 정보'
        ])

    # 파일 첨부가 있는 경우
    file_ids = inquiry.get('file_ids', '[]')
    if file_ids != '[]' and file_ids != 'null':
        contexts.append('첨부 이미지 분석 (스크린샷 내용 파악)')

    return contexts

def analyze_consistency_with_past(inquiry, all_comments):
    """과거 응답과의 일관성 분석"""
    inquiry_type = categorize_inquiry_type(
        inquiry.get('title', ''),
        strip_html_tags(inquiry.get('content', ''))
    )

    # 해당 문의의 댓글
    inquiry_id = inquiry.get('id')
    inquiry_comments = [c for c in all_comments if c.get('inquiry_id') == inquiry_id]

    admin_comments = [c for c in inquiry_comments if c.get('is_admin') == 1]

    if not admin_comments:
        return {
            'has_past_response': False,
            'consistency_possible': False,
            'note': '운영자 답변 없음'
        }

    # 과거 응답 패턴 분석
    response_patterns = []
    for comment in admin_comments:
        response_text = strip_html_tags(comment.get('content', ''))

        # 응답 패턴 분류
        if '조치' in response_text and len(response_text) < 50:
            response_patterns.append('단순_조치_완료')
        elif '안내' in response_text or '설명' in response_text:
            response_patterns.append('가이드_제공')
        elif len(response_text) > 100:
            response_patterns.append('상세_설명')
        else:
            response_patterns.append('간단_답변')

    # 일관성 판단
    if inquiry_type == '계정/권한':
        consistency_analysis = {
            'has_past_response': True,
            'consistency_possible': True,
            'response_pattern': '단순_조치_완료',
            'recommendation': '과거 응답 참조하여 "조치 완료" 패턴 유지 가능, 단 Agent는 실제 조치 불가능하므로 운영자 에스컬레이션 필요',
            'can_agent_respond': False
        }
    elif inquiry_type == '학습/과제':
        consistency_analysis = {
            'has_past_response': True,
            'consistency_possible': True,
            'response_pattern': '가이드_제공' if '가이드_제공' in response_patterns else '상세_설명',
            'recommendation': '과거 응답 스타일을 학습하여 유사한 톤과 형식으로 답변 가능',
            'can_agent_respond': True
        }
    else:
        consistency_analysis = {
            'has_past_response': True,
            'consistency_possible': True if response_patterns else False,
            'response_pattern': response_patterns[0] if response_patterns else 'N/A',
            'recommendation': 'Agent가 답변 가능 여부는 문의 구체성에 따라 판단 필요',
            'can_agent_respond': 'conditional'
        }

    return consistency_analysis

def main():
    """메인 분석 함수"""
    # 데이터 로드
    print("데이터 로딩 중...")
    with open('inquiry.json', 'r', encoding='utf-8') as f:
        inquiries = json.load(f)

    with open('inquiry_comment.json', 'r', encoding='utf-8') as f:
        comments = json.load(f)

    with open('files.json', 'r', encoding='utf-8') as f:
        files = json.load(f)

    print(f"총 {len(inquiries)}개의 문의, {len(comments)}개의 댓글, {len(files)}개의 파일")

    # 분석 결과 저장
    analysis_results = []

    print("\n문의 분석 중...")
    for inquiry in inquiries:
        inquiry_id = inquiry.get('id')
        title = inquiry.get('title', '')
        content_html = inquiry.get('content', '')
        content = strip_html_tags(content_html)
        author_id = inquiry.get('author_id')
        file_ids = inquiry.get('file_ids', '[]')
        status = inquiry.get('status', '')
        is_pinned = inquiry.get('is_pinned', 0)
        create_dt = inquiry.get('create_dt', '')

        # 해당 문의의 댓글
        inquiry_comments = [c for c in comments if c.get('inquiry_id') == inquiry_id]

        # 유형 분류
        inquiry_type = categorize_inquiry_type(title, content)

        # 답변 가능성 분석
        answerability_info = analyze_answerability(inquiry, inquiry_comments)

        # 필요한 context 식별
        required_contexts = identify_required_context(inquiry, inquiry_type, answerability_info)

        # 과거 응답 일관성 분석
        consistency_info = analyze_consistency_with_past(inquiry, comments)

        # 다국어 여부 확인
        is_multilingual = False
        detected_language = 'Korean'
        # 간단한 언어 감지 (일본어 문자, 영어 비율)
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', content):
            is_multilingual = True
            detected_language = 'Japanese'
        elif len(re.findall(r'[a-zA-Z]', content)) / max(len(content), 1) > 0.5:
            is_multilingual = True
            detected_language = 'English'

        # 첨부 파일 정보
        has_attachment = file_ids not in ['[]', 'null', None, '']

        # Admin 응답 정보
        admin_responses = [c for c in inquiry_comments if c.get('is_admin') == 1]
        admin_response_summary = ''
        if admin_responses:
            admin_response_summary = strip_html_tags(admin_responses[0].get('content', ''))[:100]

        # 결과 저장
        result = {
            'inquiry_id': inquiry_id,
            'title': title,
            'content_preview': content[:200] if len(content) > 200 else content,
            'author_id': author_id,
            'create_date': create_dt,
            'status': status,
            'is_pinned': is_pinned,
            'inquiry_type': inquiry_type,
            'answerability': answerability_info['answerability'],
            'answerability_reason': answerability_info['reason'],
            'confidence': answerability_info['confidence'],
            'required_contexts': ' | '.join(required_contexts),
            'has_past_response': consistency_info.get('has_past_response', False),
            'can_agent_respond': consistency_info.get('can_agent_respond', 'unknown'),
            'response_pattern': consistency_info.get('response_pattern', 'N/A'),
            'consistency_recommendation': consistency_info.get('recommendation', 'N/A'),
            'has_attachment': has_attachment,
            'attachment_analysis_needed': has_attachment,
            'language': detected_language,
            'is_multilingual': is_multilingual,
            'admin_response_summary': admin_response_summary,
            'num_comments': len(inquiry_comments),
            'num_admin_comments': len(admin_responses)
        }

        analysis_results.append(result)

    # CSV 저장
    print("\nCSV 파일 생성 중...")
    csv_filename = 'inquiry_analysis_report.csv'

    fieldnames = [
        'inquiry_id', 'title', 'content_preview', 'author_id', 'create_date', 'status', 'is_pinned',
        'inquiry_type', 'answerability', 'answerability_reason', 'confidence',
        'required_contexts', 'has_past_response', 'can_agent_respond', 'response_pattern',
        'consistency_recommendation', 'has_attachment', 'attachment_analysis_needed',
        'language', 'is_multilingual', 'admin_response_summary', 'num_comments', 'num_admin_comments'
    ]

    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(analysis_results)

    print(f"[완료] 분석 완료: {csv_filename}")

    # 요약 통계
    print("\n" + "="*80)
    print("분석 결과 요약")
    print("="*80)

    # 답변 가능성 통계
    answerability_counts = {}
    for result in analysis_results:
        ans = result['answerability']
        answerability_counts[ans] = answerability_counts.get(ans, 0) + 1

    print("\n1. 답변 가능성 분포:")
    for ans_type, count in sorted(answerability_counts.items()):
        percentage = (count / len(analysis_results)) * 100
        print(f"   - {ans_type}: {count}건 ({percentage:.1f}%)")

    # 문의 유형 통계
    type_counts = {}
    for result in analysis_results:
        itype = result['inquiry_type']
        type_counts[itype] = type_counts.get(itype, 0) + 1

    print("\n2. 문의 유형 분포:")
    for itype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(analysis_results)) * 100
        print(f"   - {itype}: {count}건 ({percentage:.1f}%)")

    # Agent 응답 가능 여부
    agent_can_respond = sum(1 for r in analysis_results if r['can_agent_respond'] == True)
    agent_cannot_respond = sum(1 for r in analysis_results if r['can_agent_respond'] == False)
    agent_conditional = sum(1 for r in analysis_results if r['can_agent_respond'] == 'conditional')

    print("\n3. Agent 응답 가능성:")
    print(f"   - 응답 가능: {agent_can_respond}건")
    print(f"   - 응답 불가능: {agent_cannot_respond}건")
    print(f"   - 조건부 가능: {agent_conditional}건")

    # 첨부 파일
    with_attachment = sum(1 for r in analysis_results if r['has_attachment'])
    print(f"\n4. 첨부 파일:")
    print(f"   - 첨부 파일 있음: {with_attachment}건")
    print(f"   - 첨부 파일 없음: {len(analysis_results) - with_attachment}건")

    # 다국어
    multilingual = sum(1 for r in analysis_results if r['is_multilingual'])
    print(f"\n5. 다국어:")
    print(f"   - 한국어: {len(analysis_results) - multilingual}건")
    print(f"   - 기타 언어: {multilingual}건")

    language_counts = {}
    for result in analysis_results:
        lang = result['language']
        language_counts[lang] = language_counts.get(lang, 0) + 1
    for lang, count in sorted(language_counts.items()):
        print(f"      · {lang}: {count}건")

    print("\n" + "="*80)
    print("\n필요한 Context 종류:")
    print("="*80)

    all_contexts = set()
    for result in analysis_results:
        contexts = result['required_contexts'].split(' | ')
        all_contexts.update(contexts)

    for i, context in enumerate(sorted(all_contexts), 1):
        print(f"{i}. {context}")

    print("\n분석 완료!")

if __name__ == '__main__':
    main()
