"""
C:/atl_scrape/inquiry_output/inquiry_full.json
→ inquiry_test.json + inquiry_comment_test.json

Train 파일(inquiry.json, inquiry_comment.json)과 동일한 형식으로 변환.
ID 충돌 방지: inquiry 101~, comment 121~, user author 20001~
"""

import json
import re
from pathlib import Path


# ── 날짜 파싱 ──────────────────────────────────────────────
def parse_date(date_str: str) -> str:
    """
    "2025. 12. 14. 오후 08:51" → "2025-12-14 20:51:00"
    "2026. 02. 27. 오전 06:34" → "2026-02-27 06:34:00"
    """
    if not date_str:
        return "2026-01-01 00:00:00"
    m = re.match(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(오전|오후)\s*(\d{1,2}):(\d{2})', date_str)
    if not m:
        return "2026-01-01 00:00:00"
    year, month, day, ampm, hour, minute = m.groups()
    hour = int(hour)
    if ampm == '오후' and hour != 12:
        hour += 12
    elif ampm == '오전' and hour == 12:
        hour = 0
    return f"{year}-{int(month):02d}-{int(day):02d} {hour:02d}:{int(minute):02d}:00"


def text_to_html(text: str) -> str:
    """Plain text → 간단한 HTML (줄바꿈 → <br>)"""
    if not text:
        return ""
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lines = escaped.split('\n')
    paragraphs = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            paragraphs.append(f"<p>{stripped}</p>")
    return "".join(paragraphs) if paragraphs else "<p></p>"


def is_valid_record(record: dict) -> bool:
    """의미 없는 레코드 필터 (가이드 공지, 빈 내용)"""
    q = record.get("question_text", "").strip()
    title = record.get("title", "").strip()
    if not q or q in (".", ""):
        return False
    if not title or title in (".", ""):
        return False
    # 길이 필터 (너무 짧은 문의)
    if len(q) < 5:
        return False
    return True


def main():
    src = Path("C:/atl_scrape/inquiry_output/inquiry_full.json")
    out_dir = Path(__file__).parent

    with open(src, encoding="utf-8") as f:
        full_data = json.load(f)

    inquiries_out = []
    comments_out  = []

    inquiry_id_counter = 101       # train: 9~94
    comment_id_counter = 121       # train: 7~120
    user_id_counter    = 20001     # 가상 사용자 ID

    # Admin IDs — train 데이터와 동일하게 2, 7 사용
    ADMIN_ID = 2

    # 저자명 → 가상 ID 매핑 (동일 저자는 동일 ID 부여)
    author_id_map: dict[str, int] = {}

    def get_user_id(author_name: str) -> int:
        nonlocal user_id_counter
        if author_name not in author_id_map:
            author_id_map[author_name] = user_id_counter
            user_id_counter += 1
        return author_id_map[author_name]

    for record in full_data:
        if not is_valid_record(record):
            continue

        post_id     = record.get("post_id", "")
        title       = record.get("title", "")
        q_text      = record.get("question_text", "")
        q_author    = record.get("question_author", "unknown")
        q_date      = record.get("question_date", "")
        raw_status  = record.get("status", "")
        answers     = record.get("answers", []) or []

        status = "closed" if raw_status == "답변 완료" else "open"
        create_dt = parse_date(q_date)

        # 마지막 답변 날짜를 update_dt 로
        last_answer_dates = [parse_date(a.get("date", "")) for a in answers if a.get("date")]
        update_dt = last_answer_dates[-1] if last_answer_dates else create_dt

        inquiry_id = inquiry_id_counter
        inquiry_id_counter += 1

        inquiries_out.append({
            "id":         inquiry_id,
            "title":      title,
            "content":    text_to_html(q_text),
            "author_id":  get_user_id(q_author),
            "file_ids":   "[]",
            "group_id":   None,
            "status":     status,
            "is_pinned":  0,
            "create_dt":  create_dt,
            "update_dt":  update_dt,
        })

        # 댓글 변환
        for ans in answers:
            ans_text    = ans.get("text", "").strip()
            ans_author  = ans.get("author", "")
            ans_date    = ans.get("date", "")
            is_admin    = 1 if ans.get("is_admin") else 0
            author_id   = ADMIN_ID if is_admin else get_user_id(ans_author)

            if not ans_text:
                continue

            comment_create = parse_date(ans_date)
            comments_out.append({
                "id":          comment_id_counter,
                "inquiry_id":  inquiry_id,
                "content":     text_to_html(ans_text),
                "author_id":   author_id,
                "file_ids":    None,
                "is_admin":    is_admin,
                "create_dt":   comment_create,
                "update_dt":   comment_create,
            })
            comment_id_counter += 1

    # 저장
    inq_path = out_dir / "inquiry_test.json"
    cmt_path = out_dir / "inquiry_comment_test.json"

    with open(inq_path, "w", encoding="utf-8") as f:
        json.dump(inquiries_out, f, ensure_ascii=False, indent="\t")
    with open(cmt_path, "w", encoding="utf-8") as f:
        json.dump(comments_out, f, ensure_ascii=False, indent="\t")

    print(f"변환 완료!")
    print(f"  inquiry_test.json       : {len(inquiries_out)}건 → {inq_path}")
    print(f"  inquiry_comment_test.json: {len(comments_out)}건 → {cmt_path}")

    # ID 범위 확인
    if inquiries_out:
        ids = [i["id"] for i in inquiries_out]
        print(f"  Inquiry ID 범위: {min(ids)} ~ {max(ids)}")
    if comments_out:
        cids = [c["id"] for c in comments_out]
        print(f"  Comment ID 범위: {min(cids)} ~ {max(cids)}")


if __name__ == "__main__":
    main()
