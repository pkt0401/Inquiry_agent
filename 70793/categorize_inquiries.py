"""
AI Talent Lab 문의하기 유형별 분류 및 답변 전략 수립

목적:
1. 문의를 세부 유형으로 레이블링
2. 각 유형별 Agent 답변 전략 결정 (답변 안함 / Prompt 직접 / Tool calling + RAG)
3. 보수적 답변 기준 설정
"""

import json
import csv
from html import unescape
from html.parser import HTMLParser

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

def categorize_inquiry(inquiry, comments):
    """
    문의 세부 분류 및 답변 전략 결정

    반환:
    {
        'label': '레이블명',
        'should_respond': True/False,  # Agent가 답변해야 하는지
        'strategy': 'no_response' / 'prompt_direct' / 'tool_rag',
        'examples': [...],  # 유사 사례
        'rationale': '판단 근거'
    }
    """
    title = inquiry.get('title', '').lower()
    content = strip_html_tags(inquiry.get('content', '')).lower()
    text = title + " " + content

    # 관리자 답변 확인
    admin_responses = [c for c in comments if c.get('is_admin') == 1]
    has_admin_response = len(admin_responses) > 0

    admin_response_text = ''
    if has_admin_response:
        admin_response_text = strip_html_tags(admin_responses[0].get('content', ''))

    # ==================== 답변 불필요 (운영자 에스컬레이션) ====================

    # 1. 개인 계정 조치 필요
    if any(kw in text for kw in ['버튼', '비활성화', '활성화', '권한', '접근', '조치']) and \
       any(kw in text for kw in ['인증', '시작하기', '제출', '버튼']):
        return {
            'label': 'ACCOUNT_ACTION_REQUIRED',
            'label_kr': '개인 계정 조치 필요',
            'should_respond': False,
            'strategy': 'no_response',
            'action': '운영자 티켓 자동 생성 + 안내 메시지',
            'rationale': '개인 계정 DB 직접 조작 필요, Agent 권한 없음',
            'response_template': '''
안녕하세요.

해당 문의는 개인 계정 확인 및 시스템 조치가 필요한 사항입니다.
운영팀에 문의를 전달하였으며, 빠른 시일 내에 조치 후 답변드리겠습니다.

감사합니다.
            '''.strip()
        }

    # 2. 플랫폼 시스템 에러 (백엔드 문제)
    if 'console' in text or 'script 실행' in text or '접근이 안' in text:
        if '에러' in text or 'error' in text or '안됩니다' in text or '안되' in text:
            return {
                'label': 'PLATFORM_SYSTEM_ERROR',
                'label_kr': '플랫폼 시스템 에러',
                'should_respond': False,
                'strategy': 'no_response',
                'action': '운영자 티켓 자동 생성 (우선순위: 높음)',
                'rationale': '플랫폼 백엔드 문제, 시스템 로그 확인 및 긴급 조치 필요',
                'response_template': '''
안녕하세요.

해당 문제는 플랫폼 시스템 점검이 필요한 사항입니다.
운영팀에서 긴급히 확인 중이며, 빠른 시일 내에 조치 후 답변드리겠습니다.

감사합니다.
            '''.strip()
            }

    # ==================== Prompt 직접 답변 (간단한 FAQ) ====================

    # 3. 제출 규정 관련
    if any(kw in text for kw in ['제출', '여러번', '다시', '재제출', '기한', '마감']):
        if any(kw in text for kw in ['과제', '문서', '소스코드', '최종']):
            return {
                'label': 'SUBMISSION_POLICY',
                'label_kr': '과제 제출 규정',
                'should_respond': True,
                'strategy': 'prompt_direct',
                'action': 'FAQ에서 직접 답변',
                'rationale': '명확한 정책, 과거 답변 일관됨',
                'required_context': [
                    'FAQ: 과제 제출 규정',
                    '과거 답변 패턴'
                ],
                'example_response': '''
안녕하세요.

최종과제의 기획 설계 문서와 소스코드는 여러번 제출 가능하십니다.
단, 마감 기한 이내에 제출하신 최종 버전으로 평가됩니다.

감사합니다.
                '''.strip()
            }

    # 4. 인증 버튼 정책 안내 (조치는 안하지만 설명은 가능)
    if '인증' in text and '버튼' in text and '비활성화' in text:
        # 단, 설명만 하고 실제 조치는 운영자에게
        if '안내' in admin_response_text or '대상' in admin_response_text:
            return {
                'label': 'CERTIFICATION_POLICY_INFO',
                'label_kr': '인증 정책 안내 (조치는 불가)',
                'should_respond': True,
                'strategy': 'prompt_direct',
                'action': 'FAQ에서 정책 안내 + 필요 시 운영자 티켓',
                'rationale': '정책은 설명 가능, 단 실제 활성화는 운영자만 가능',
                'required_context': [
                    'FAQ: 인증 시험 정책',
                    '인증 대상자 기준 (공개 가능 범위)'
                ],
                'example_response': '''
안녕하세요.

AI Literacy 인증 시작하기 버튼은 인증 시험 응시자 대상으로 기간 내 활성화됩니다.
인증 대상자 안내를 받지 않으셨다면 비활성화 상태가 정상 상태입니다.

만약 인증 대상자 안내를 받으셨는데도 버튼이 비활성화 상태라면,
운영팀에서 확인 후 조치해드리겠습니다.

감사합니다.
                '''.strip(),
                'escalate_if': '사용자가 대상자라고 주장하는 경우'
            }

    # 5. 강의 안내
    if any(kw in text for kw in ['강의', '수강', '듣고 싶', '어디서', '찾기']):
        return {
            'label': 'COURSE_INFO',
            'label_kr': '강의/수강 안내',
            'should_respond': True,
            'strategy': 'prompt_direct',
            'action': 'FAQ에서 직접 답변',
            'rationale': '정적인 정보, FAQ로 충분',
            'required_context': [
                'FAQ: 강의 목록 및 커리큘럼',
                '수강 신청 방법'
            ]
        }

    # 6. 서비스 이용 가이드
    if '가이드' in title or '작성' in title:
        return {
            'label': 'SERVICE_GUIDE',
            'label_kr': '서비스 이용 가이드',
            'should_respond': True,
            'strategy': 'prompt_direct',
            'action': 'FAQ 또는 공지사항 링크 제공',
            'rationale': '정적 문서, 링크 제공으로 충분',
            'required_context': [
                '가이드 문서 링크',
                '공지사항'
            ]
        }

    # ==================== Tool Calling + RAG ====================

    # 7. 플랫폼 API 사용법 문의 (환경은 이미 설정됨, 사용법만 문의)
    if 'api' in text and ('key' in text or 'openai' in text or 'azure' in text):
        if '설정' in text or '사용' in text or '방법' in text or '어떻게' in text:
            return {
                'label': 'PLATFORM_API_USAGE',
                'label_kr': '플랫폼 API 사용법',
                'should_respond': True,
                'strategy': 'prompt_direct',
                'action': 'FAQ에서 플랫폼 API 사용 가이드 제공',
                'rationale': '플랫폼에서 제공하는 API 사용법, 가이드 문서로 충분',
                'required_context': [
                    'FAQ: 플랫폼 API 사용 가이드',
                    '코드 예시'
                ]
            }

    # 8. 코드 로직 에러 (사용자 코드 문제)
    if '코드' in text or 'code' in text:
        if 'error' in text or '에러' in text or '오류' in text:
            return {
                'label': 'CODE_LOGIC_ERROR',
                'label_kr': '코드 로직 에러',
                'should_respond': True,
                'strategy': 'tool_rag',
                'action': 'RAG로 유사 에러 검색 + Tool로 코드 분석 및 수정 제안',
                'rationale': '사용자 작성 코드 문제, 과거 유사 사례 및 디버깅 가이드 제공',
                'required_context': [
                    'RAG: 과거 코드 에러 해결 사례',
                    'Tool: 에러 메시지 분석',
                    'Tool: 코드 디버깅 제안'
                ],
                'tools_needed': [
                    'search_similar_code_errors(error_message)',
                    'analyze_code(code_snippet)',
                    'suggest_fix(error_type, code)'
                ]
            }

    # 9. 과제 개발 문의 (복잡)
    if '과제' in text and any(kw in text for kw in ['개발', '구현', '어떻게', '방법']):
        return {
            'label': 'ASSIGNMENT_DEVELOPMENT',
            'label_kr': '과제 개발 방법 문의',
            'should_respond': True,
            'strategy': 'tool_rag',
            'action': 'RAG로 유사 과제 검색 + Tool로 코드 예시 생성',
            'rationale': '개별 과제마다 다름, 과거 사례 및 예시 필요',
            'required_context': [
                'RAG: 과거 과제 Q&A',
                'Tool: 코드 예시 생성',
                'Tool: 참고 자료 검색'
            ],
            'tools_needed': [
                'search_similar_assignments(topic)',
                'generate_code_template(task)',
                'search_references(topic)'
            ]
        }

    # 10. 강의 영상 재생 오류
    if '강의' in text and ('영상' in text or '비디오' in text or '재생' in text):
        if '안' in text or '오류' in text or 'error' in text:
            return {
                'label': 'VIDEO_PLAYBACK_ERROR',
                'label_kr': '강의 영상 재생 오류',
                'should_respond': True,
                'strategy': 'prompt_direct',
                'action': 'FAQ에서 일반적인 해결방법 안내',
                'rationale': '일반적인 트러블슈팅 가이드로 충분',
                'required_context': [
                    'FAQ: 영상 재생 트러블슈팅',
                    '브라우저 권장 사항'
                ]
            }

    # 11. 건의/개선 요청
    if any(kw in text for kw in ['건의', '개선', '요청', '추가', '제안']):
        return {
            'label': 'FEATURE_REQUEST',
            'label_kr': '기능 개선/건의',
            'should_respond': True,
            'strategy': 'prompt_direct',
            'action': '감사 메시지 + 전달 확인',
            'rationale': '단순 접수 확인, 복잡한 처리 불필요',
            'required_context': [
                '건의 접수 정책'
            ],
            'example_response': '''
안녕하세요.

소중한 의견 감사드립니다.
건의해주신 내용은 서비스 개선에 적극 반영하도록 하겠습니다.

감사합니다.
            '''.strip()
        }

    # ==================== 기타 (판단 필요) ====================

    return {
        'label': 'UNCATEGORIZED',
        'label_kr': '미분류 (검토 필요)',
        'should_respond': False,
        'strategy': 'no_response',
        'action': '운영자 검토',
        'rationale': '명확한 분류 불가, 안전하게 운영자에게',
        'required_context': []
    }

def main():
    """메인 실행"""
    print("데이터 로딩 중...")
    with open('inquiry.json', 'r', encoding='utf-8') as f:
        inquiries = json.load(f)

    with open('inquiry_comment.json', 'r', encoding='utf-8') as f:
        all_comments = json.load(f)

    print(f"총 {len(inquiries)}개의 문의 분석 중...\n")

    # 레이블별 그룹화
    label_groups = {}
    results = []

    for inquiry in inquiries:
        inquiry_id = inquiry.get('id')
        title = inquiry.get('title', '')
        content = strip_html_tags(inquiry.get('content', ''))

        # 해당 문의의 댓글
        comments = [c for c in all_comments if c.get('inquiry_id') == inquiry_id]

        # 분류
        category_info = categorize_inquiry(inquiry, comments)

        # 결과 저장
        result = {
            'inquiry_id': inquiry_id,
            'title': title,
            'content_preview': content[:150],
            'label': category_info['label'],
            'label_kr': category_info['label_kr'],
            'should_respond': category_info['should_respond'],
            'strategy': category_info['strategy'],
            'action': category_info['action'],
            'rationale': category_info['rationale']
        }
        results.append(result)

        # 그룹화
        label = category_info['label']
        if label not in label_groups:
            label_groups[label] = {
                'info': category_info,
                'examples': []
            }
        label_groups[label]['examples'].append({
            'id': inquiry_id,
            'title': title,
            'preview': content[:100]
        })

    # CSV 저장
    print("CSV 생성 중...")
    with open('inquiry_categorization.csv', 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'inquiry_id', 'title', 'content_preview', 'label', 'label_kr',
            'should_respond', 'strategy', 'action', 'rationale'
        ])
        writer.writeheader()
        writer.writerows(results)

    print("[완료] inquiry_categorization.csv 생성 완료\n")

    # 레이블별 요약 출력
    print("="*80)
    print("문의 유형별 분류 및 답변 전략")
    print("="*80)

    # 답변 안함
    print("\n[1] 답변 안함 (운영자 에스컬레이션)")
    print("-" * 80)
    for label, data in label_groups.items():
        if not data['info']['should_respond']:
            print(f"\n■ {data['info']['label_kr']} ({label})")
            print(f"  전략: {data['info']['strategy']}")
            print(f"  조치: {data['info']['action']}")
            print(f"  근거: {data['info']['rationale']}")
            if 'response_template' in data['info']:
                print(f"  안내 메시지 템플릿:")
                for line in data['info']['response_template'].split('\n'):
                    print(f"    {line}")
            print(f"\n  예시 ({len(data['examples'])}건):")
            for ex in data['examples'][:3]:
                print(f"    - ID {ex['id']}: {ex['title']}")

    # Prompt 직접 답변
    print("\n\n[2] Prompt 직접 답변 (간단한 FAQ)")
    print("-" * 80)
    for label, data in label_groups.items():
        if data['info']['should_respond'] and data['info']['strategy'] == 'prompt_direct':
            print(f"\n■ {data['info']['label_kr']} ({label})")
            print(f"  전략: {data['info']['strategy']}")
            print(f"  조치: {data['info']['action']}")
            print(f"  근거: {data['info']['rationale']}")
            print(f"  필요 Context:")
            for ctx in data['info'].get('required_context', []):
                print(f"    - {ctx}")
            if 'example_response' in data['info']:
                print(f"  답변 예시:")
                for line in data['info']['example_response'].split('\n'):
                    print(f"    {line}")
            print(f"\n  예시 ({len(data['examples'])}건):")
            for ex in data['examples'][:3]:
                print(f"    - ID {ex['id']}: {ex['title']}")

    # Tool Calling + RAG
    print("\n\n[3] Tool Calling + RAG (복잡한 문의)")
    print("-" * 80)
    for label, data in label_groups.items():
        if data['info']['should_respond'] and data['info']['strategy'] == 'tool_rag':
            print(f"\n■ {data['info']['label_kr']} ({label})")
            print(f"  전략: {data['info']['strategy']}")
            print(f"  조치: {data['info']['action']}")
            print(f"  근거: {data['info']['rationale']}")
            print(f"  필요 Context:")
            for ctx in data['info'].get('required_context', []):
                print(f"    - {ctx}")
            if 'tools_needed' in data['info']:
                print(f"  필요 Tools:")
                for tool in data['info']['tools_needed']:
                    print(f"    - {tool}")
            print(f"\n  예시 ({len(data['examples'])}건):")
            for ex in data['examples'][:3]:
                print(f"    - ID {ex['id']}: {ex['title']}")

    print("\n" + "="*80)
    print("분석 완료!")
    print("="*80)

if __name__ == '__main__':
    main()
