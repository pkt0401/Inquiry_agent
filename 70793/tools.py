"""
tools.py — Agent Tool 정의 및 실행기

Tool 종류:
  AUTO_TOOL     : 즉시 실행 (저위험, 단순 복구)
  APPROVAL_TOOL : 관리자 승인 후 실행 (고위험·비가역적 액션, 추후 추가)

새 Tool 추가 방법:
  1. inquiry_agent.py의 InquiryLabel에 라벨 추가
  2. AUTO_TOOLS 또는 APPROVAL_TOOLS에 라벨 등록
  3. execute_tool_action()에 처리 분기 추가
  4. knowledge_base.json label_examples에 예시 추가
"""

import re
from typing import Dict, Optional, Tuple
from user_db import UserContextDB, CODE_REVIEW_DAILY_LIMIT, PRACTICE_DEFAULT_RESTORE


# ──────────────────────────────────────────────────────────────────
# Tool 그룹 정의  (InquiryLabel 값을 문자열로 관리 — 순환 import 방지)
# ──────────────────────────────────────────────────────────────────

# AUTO TOOL: 즉시 실행 (저위험, 단순 복구)
AUTO_TOOL_LABELS: set[str] = {
    "CODE_REVIEW_RESET",
    "LITERACY_PRACTICE_RESET",
}

# APPROVAL TOOL: 관리자 승인 후 실행 (추후 추가)
APPROVAL_TOOL_LABELS: set[str] = set()

GROUP3_LABELS: set[str] = AUTO_TOOL_LABELS | APPROVAL_TOOL_LABELS


def get_tool_type(label_value: str) -> str:
    """라벨 값을 받아 'auto' 또는 'approval'을 반환."""
    if label_value in AUTO_TOOL_LABELS:
        return "auto"
    if label_value in APPROVAL_TOOL_LABELS:
        return "approval"
    return "unknown"


# ──────────────────────────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────────────────────────

def extract_count_from_text(text: str) -> int:
    """
    문의 텍스트에서 복구 요청 횟수를 추출.
    명시되지 않으면 PRACTICE_DEFAULT_RESTORE 반환.
    """
    m = re.search(r'(\d+)\s*(?:번|회|개|times?)', text)
    return int(m.group(1)) if m else PRACTICE_DEFAULT_RESTORE


# ──────────────────────────────────────────────────────────────────
# Tool 실행기
# ──────────────────────────────────────────────────────────────────

def execute_tool_action(
    label_value: str,
    author_id: Optional[int],
    inquiry_text: str,
    user_db: UserContextDB,
) -> Tuple[str, Dict, str]:
    """
    GROUP3 라벨에 대응하는 실제 액션을 실행.

    Parameters
    ----------
    label_value  : InquiryLabel.value 문자열
    author_id    : 문의자 user id (없으면 None)
    inquiry_text : 제목 + 본문 평문 (횟수 추출용)
    user_db      : UserContextDB 인스턴스

    Returns
    -------
    (answer_text, tool_result, tool_type)
    """
    tool_type = get_tool_type(label_value)

    if not author_id:
        answer = (
            "안녕하세요, AI Talent Lab입니다.\n"
            "요청을 처리하려면 로그인 정보가 필요합니다. 담당자에게 문의해 주세요.\n\n감사합니다."
        )
        return answer, {"success": False, "reason": "author_id 없음"}, tool_type

    # ── AUTO TOOLS ─────────────────────────────────────────────────

    if label_value == "CODE_REVIEW_RESET":
        result = user_db.reset_review_count(author_id)
        answer = (
            f"안녕하세요, AI Talent Lab입니다.\n"
            f"코드 리뷰 횟수를 초기화했습니다. "
            f"오늘 다시 {CODE_REVIEW_DAILY_LIMIT}회 요청하실 수 있습니다.\n\n감사합니다."
        )
        return answer, result, tool_type

    if label_value == "LITERACY_PRACTICE_RESET":
        count = extract_count_from_text(inquiry_text)
        result = user_db.restore_practice_count(author_id, count)
        answer = (
            f"안녕하세요, AI Talent Lab입니다.\n"
            f"AI Literacy 사전연습 횟수 {count}회를 복구했습니다. "
            f"다시 연습하실 수 있습니다.\n\n감사합니다."
        )
        return answer, result, tool_type

    # ── APPROVAL TOOLS (추후 추가) ─────────────────────────────────

    # 알 수 없는 라벨 (방어 코드)
    return (
        "안녕하세요, AI Talent Lab입니다.\n요청을 처리할 수 없습니다. 담당자에게 문의해 주세요.\n\n감사합니다.",
        {"success": False, "reason": f"미지원 액션: {label_value}"},
        tool_type,
    )
