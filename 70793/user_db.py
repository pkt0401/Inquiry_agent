"""
user_db.py — 수강생 개인화 데이터 (SQLite)

테이블:
  users       : 수강생 기본 정보
  cohorts     : 기수 정보 (프로그램별)
  enrollments : 수강 이력 (기수별 수료/미수료/진행중)

PoC 용 더미 데이터를 포함.
실서비스에서는 PostgreSQL 등으로 교체 가능 (SQLAlchemy 기반으로 변경하면 됨).
"""

import sqlite3
import os
import random
from typing import Dict, List, Optional


DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_data.db")


# ──────────────────────────────────────────────────────────────────
# DB 초기화 / 스키마
# ──────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,
    name        TEXT,
    email       TEXT
);

CREATE TABLE IF NOT EXISTS cohorts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    program         TEXT NOT NULL,   -- 'AI Bootcamp' | 'AI Literacy' | 'AI Master Project'
    cohort_name     TEXT NOT NULL,   -- '10기' | '11기' | '12기' 등
    start_dt        TEXT,
    end_dt          TEXT
);

CREATE TABLE IF NOT EXISTS enrollments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    cohort_id   INTEGER NOT NULL,
    status      TEXT NOT NULL,   -- 'completed' | 'failed' | 'in_progress'
    final_score REAL,
    note        TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (cohort_id) REFERENCES cohorts(id)
);
"""

STATUS_KO = {
    "completed":   "수료",
    "failed":      "미수료",
    "in_progress": "진행중",
}


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH):
    """DB 파일이 없으면 스키마 생성 + 더미 데이터 삽입."""
    exists = os.path.exists(db_path)
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    if not exists:
        _insert_dummy_data(conn)
    conn.close()


# ──────────────────────────────────────────────────────────────────
# 더미 데이터
# ──────────────────────────────────────────────────────────────────

# inquiry_all.json 의 실제 author_id 목록 (110건 전체 기준)
KNOWN_AUTHOR_IDS = [
    2, 277, 312, 400, 404, 752, 1133, 1194, 1256, 1306,
    1467, 1512, 1792, 1846, 1882, 1910, 2045, 2343, 2384, 2607,
    2656, 2710, 2844, 2860, 2894, 2969, 2985, 2996, 3010, 3023,
    3346, 3405, 3406, 3417, 3508, 3518, 3571, 3600, 3621, 3627,
    3646, 3652, 3658, 3691, 3710, 3890, 4011, 4100, 4183, 4358,
    4403, 4560, 4586, 7918, 7938, 8137, 8193, 8540, 8660, 11262,
    11306, 20002, 20003, 20004, 20005, 20006, 20007, 20008, 20009, 20010,
    20011, 20012, 20013, 20014, 20015, 20016, 20017, 20020, 20021, 20022,
    20024, 20026, 20027, 20028, 20029, 20063,
]

COHORT_DATA = [
    # (program, cohort_name, start_dt, end_dt)
    ("AI Bootcamp", "9기",  "2025-06-02", "2025-07-11"),
    ("AI Bootcamp", "10기", "2025-08-04", "2025-09-12"),
    ("AI Bootcamp", "11기", "2025-10-06", "2025-11-14"),
    ("AI Bootcamp", "12기", "2026-02-23", "2026-03-20"),   # 현재 진행 중 (schedule.json 기준)
    ("AI Literacy", "상시", "2024-01-01", "2099-12-31"),    # 상시 운영
    ("AI Master Project", "1기", "2025-04-01", "2025-07-31"),
]


def _insert_dummy_data(conn: sqlite3.Connection):
    random.seed(42)

    # cohorts
    cohort_ids = {}
    for program, cohort_name, start_dt, end_dt in COHORT_DATA:
        cur = conn.execute(
            "INSERT INTO cohorts (program, cohort_name, start_dt, end_dt) VALUES (?,?,?,?)",
            (program, cohort_name, start_dt, end_dt),
        )
        cohort_ids[(program, cohort_name)] = cur.lastrowid
    conn.commit()

    bc_12  = cohort_ids[("AI Bootcamp", "12기")]
    bc_11  = cohort_ids[("AI Bootcamp", "11기")]
    bc_10  = cohort_ids[("AI Bootcamp", "10기")]
    lit    = cohort_ids[("AI Literacy", "상시")]

    for uid in KNOWN_AUTHOR_IDS:
        conn.execute("INSERT OR IGNORE INTO users (id, name, email) VALUES (?,?,?)",
                     (uid, f"user_{uid}", f"user_{uid}@example.com"))

        r = random.random()

        if r < 0.12:
            # 케이스 A: 10기 미수료 → 12기 재수강
            conn.execute(
                "INSERT INTO enrollments (user_id, cohort_id, status, final_score, note) VALUES (?,?,?,?,?)",
                (uid, bc_10, "failed", round(random.uniform(30, 59), 1), "최종과제 미제출로 미수료"),
            )
            conn.execute(
                "INSERT INTO enrollments (user_id, cohort_id, status, final_score, note) VALUES (?,?,?,?,?)",
                (uid, bc_12, "in_progress", None, "재수강"),
            )

        elif r < 0.22:
            # 케이스 B: 11기 미수료 → 12기 재수강
            conn.execute(
                "INSERT INTO enrollments (user_id, cohort_id, status, final_score, note) VALUES (?,?,?,?,?)",
                (uid, bc_11, "failed", round(random.uniform(20, 59), 1), "최종과제 점수 미달"),
            )
            conn.execute(
                "INSERT INTO enrollments (user_id, cohort_id, status, final_score, note) VALUES (?,?,?,?,?)",
                (uid, bc_12, "in_progress", None, "재수강"),
            )

        elif r < 0.50:
            # 케이스 C: 12기 신규 수강중
            conn.execute(
                "INSERT INTO enrollments (user_id, cohort_id, status, final_score, note) VALUES (?,?,?,?,?)",
                (uid, bc_12, "in_progress", None, None),
            )

        elif r < 0.65:
            # 케이스 D: AI Literacy 수강 중
            conn.execute(
                "INSERT INTO enrollments (user_id, cohort_id, status, final_score, note) VALUES (?,?,?,?,?)",
                (uid, lit, "in_progress", None, None),
            )

        elif r < 0.80:
            # 케이스 E: AI Literacy 수강 중 + Bootcamp 12기 진행중
            conn.execute(
                "INSERT INTO enrollments (user_id, cohort_id, status, final_score, note) VALUES (?,?,?,?,?)",
                (uid, lit, "in_progress", None, None),
            )
            conn.execute(
                "INSERT INTO enrollments (user_id, cohort_id, status, final_score, note) VALUES (?,?,?,?,?)",
                (uid, bc_12, "in_progress", None, None),
            )

        elif r < 0.88:
            # 케이스 F: Bootcamp 11기 수료 + AI Literacy 수료
            conn.execute(
                "INSERT INTO enrollments (user_id, cohort_id, status, final_score, note) VALUES (?,?,?,?,?)",
                (uid, bc_11, "completed", round(random.uniform(70, 100), 1), None),
            )
            conn.execute(
                "INSERT INTO enrollments (user_id, cohort_id, status, final_score, note) VALUES (?,?,?,?,?)",
                (uid, lit, "completed", None, "인증시험 합격"),
            )

        # else: 수강 이력 없음

    conn.commit()
    print(f"[user_db] 더미 데이터 삽입 완료: {len(KNOWN_AUTHOR_IDS)}명")


# ──────────────────────────────────────────────────────────────────
# 조회 API
# ──────────────────────────────────────────────────────────────────

class UserContextDB:
    """수강생 개인 맥락 조회 클래스. inquiry_agent.py 에서 사용."""

    def __init__(self, db_path: str = DB_PATH):
        init_db(db_path)
        self._db_path = db_path

    def get_user_context(self, author_id: int) -> Optional[Dict]:
        """
        author_id → 수강 이력 딕셔너리 반환.
        수강 이력이 없으면 None 반환.

        반환 예:
        {
            "user_id": 1256,
            "enrollments": [
                {"program": "AI Bootcamp", "cohort": "10기",
                 "status": "failed", "status_ko": "미수료",
                 "final_score": 45.0, "note": "최종과제 미제출로 미수료"},
                {"program": "AI Bootcamp", "cohort": "12기",
                 "status": "in_progress", "status_ko": "진행중",
                 "final_score": None, "note": "재수강"},
            ],
            "current_program": "AI Bootcamp",
            "current_cohort": "12기",
            "is_retake": True,
            "retake_from": "10기",
        }
        """
        if not author_id:
            return None

        conn = get_connection(self._db_path)
        rows = conn.execute(
            """
            SELECT c.program, c.cohort_name, c.start_dt, c.end_dt,
                   e.status, e.final_score, e.note
            FROM enrollments e
            JOIN cohorts c ON e.cohort_id = c.id
            WHERE e.user_id = ?
            ORDER BY c.start_dt
            """,
            (author_id,),
        ).fetchall()
        conn.close()

        if not rows:
            return None

        enrollments = [
            {
                "program":     r["program"],
                "cohort":      r["cohort_name"],
                "start_dt":    r["start_dt"],
                "end_dt":      r["end_dt"],
                "status":      r["status"],
                "status_ko":   STATUS_KO.get(r["status"], r["status"]),
                "final_score": r["final_score"],
                "note":        r["note"],
            }
            for r in rows
        ]

        # 현재 수강 중인 과정
        in_progress = [e for e in enrollments if e["status"] == "in_progress"]
        current = in_progress[-1] if in_progress else enrollments[-1]

        # 재수강 여부: 같은 프로그램에 failed 이력이 있으면 재수강
        failed = [e for e in enrollments if e["status"] == "failed"
                  and e["program"] == current["program"]]
        is_retake = len(failed) > 0
        retake_from = failed[-1]["cohort"] if is_retake else None

        return {
            "user_id":         author_id,
            "enrollments":     enrollments,
            "current_program": current["program"],
            "current_cohort":  current["cohort"],
            "is_retake":       is_retake,
            "retake_from":     retake_from,
        }

    def build_personal_context_str(self, author_id: int) -> str:
        """
        프롬프트에 주입할 수강생 개인 맥락 문자열 반환.
        수강 이력 없으면 빈 문자열 반환.

        예시 출력:
        ## 문의자 수강 이력
        - 현재 과정: AI Bootcamp 12기 (진행중) — 재수강 (10기 미수료 이력 있음)
        - 전체 이력:
          · AI Bootcamp 10기: 미수료 (점수: 45.0) — 최종과제 미제출로 미수료
          · AI Bootcamp 12기: 진행중
        """
        ctx = self.get_user_context(author_id)
        if not ctx:
            return ""

        lines = ["## 문의자 수강 이력"]
        current_line = f"- 현재 과정: {ctx['current_program']} {ctx['current_cohort']} ({STATUS_KO.get('in_progress','진행중')})"
        if ctx["is_retake"]:
            current_line += f" — 재수강 ({ctx['retake_from']} 미수료 이력 있음)"
        lines.append(current_line)

        lines.append("- 전체 이력:")
        for e in ctx["enrollments"]:
            score_str = f" (점수: {e['final_score']})" if e["final_score"] is not None else ""
            note_str  = f" — {e['note']}" if e["note"] else ""
            lines.append(f"  · {e['program']} {e['cohort']}: {e['status_ko']}{score_str}{note_str}")

        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────
# 간단 테스트
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    db = UserContextDB()
    print("=== 수강생 맥락 조회 테스트 ===\n")

    for uid in [1256, 400, 312, 9999]:
        print(f"--- author_id={uid} ---")
        ctx_str = db.build_personal_context_str(uid)
        print(ctx_str if ctx_str else "(수강 이력 없음)")
        print()
