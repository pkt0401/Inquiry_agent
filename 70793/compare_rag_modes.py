"""
RAG 검색 모드 비교 (답변 생성 포함)

Mode A — label-aware  : 동일 label 우선, label=None 보조
Mode B — similarity   : label 무시, 순수 유사도 상위 3개

각 테스트 문의에 대해:
  1. LLM 분류 (1회)
  2. Mode A로 RAG 검색 + 답변 생성
  3. Mode B로 RAG 검색 + 답변 생성
  → 검색된 예시 & 생성 답변을 나란히 출력

실행: venv/Scripts/python compare_rag_modes.py [테스트케이스수=3]
"""

import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from inquiry_agent import (
    InquiryAgent, load_json_file, _load_dotenv,
    html_to_text, Strategy,
)

# ── 테스트 케이스 수 (기본 3개, 인자로 조정 가능) ──────────────────
N_CASES = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def load_agent() -> InquiryAgent:
    _load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[오류] OPENAI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)

    agent = InquiryAgent(api_key=api_key)
    all_inquiries = load_json_file(os.path.join(BASE, "inquiry_all.json"))
    all_comments  = load_json_file(os.path.join(BASE, "inquiry_comment_all.json"))

    agent.load_inquiry_history(all_inquiries, all_comments, pre_label=True)
    return agent


def print_hits(hits: list, mode_name: str):
    print(f"  [{mode_name}] 검색된 예시:")
    if not hits:
        print("    (없음)")
        return
    for i, h in enumerate(hits, 1):
        lbl   = (h.get("label") or "None")[:22]
        title = h.get("title", "")[:45]
        print(f"    {i}. score={h['score']:.3f} | {h.get('type','?'):<14} | label={lbl:<22} | {title}")


def compare_one(agent: InquiryAgent, case: dict, idx: int):
    title   = case.get("title", "")
    content = html_to_text(case.get("content", ""))
    inquiry_text = title + " " + content

    print(f"\n{'═'*72}")
    print(f"테스트 {idx}: {title}")
    print(f"{'═'*72}")

    # ── Step 1: LLM 분류 (공통 1회) ──────────────────────────────
    clf = agent._llm_classify(case)
    label = clf.label
    conf  = clf.confidence_level
    print(f"  [LLM 분류]  label={label.value}  /  confidence={conf.value}")
    print(f"  [근거]      {clf.rationale}")

    # ── Mode A: label-aware ───────────────────────────────────────
    ctx_a, score_a = agent._build_kb_context(label, inquiry_text, similarity_only=False)
    hits_a = agent.vector_store.search(inquiry_text, label=label.value,
                                       top_k=3, similarity_only=False)

    # ── Mode B: similarity-only ───────────────────────────────────
    ctx_b, score_b = agent._build_kb_context(label, inquiry_text, similarity_only=True)
    hits_b = agent.vector_store.search(inquiry_text, label=label.value,
                                       top_k=3, similarity_only=True)

    # ── 검색 예시 비교 ────────────────────────────────────────────
    print()
    print_hits(hits_a, "Mode A  label-aware ")
    print_hits(hits_b, "Mode B  similarity  ")

    max_diff = score_b - score_a
    if max_diff > 0.05:
        print(f"\n  ⚠️  B가 더 높은 유사도 문서 확보 (max_score 차이: {max_diff:+.3f})")
    else:
        print(f"\n  ✅  A가 충분한 유사도로 label 문서 확보 (A={score_a:.3f}, B={score_b:.3f})")

    # ── 답변 생성 (두 모드 각각) ─────────────────────────────────
    from inquiry_agent import RAG_CONFIDENCE_THRESHOLD, Strategy as St

    base_strategy, should_respond = agent._determine_strategy(label, conf, clf)

    if not should_respond:
        print("\n  → NO_RESPONSE: 두 모드 모두 답변 생성 안 함")
        return

    # 각 모드별로 RAG 점수에 따라 독립적으로 다운그레이드 적용
    strategy_a = (St.HUMAN_REVIEW
                  if base_strategy == St.TOOL_RAG and score_a < RAG_CONFIDENCE_THRESHOLD
                  else base_strategy)
    strategy_b = (St.HUMAN_REVIEW
                  if base_strategy == St.TOOL_RAG and score_b < RAG_CONFIDENCE_THRESHOLD
                  else base_strategy)

    print(f"\n{'─'*72}")
    print("  [Mode A 답변]  (label-aware, strategy=" + strategy_a.value + ")")
    print(f"{'─'*72}")
    ans_a = agent._generate_answer(case, label, conf, ctx_a,
                                   is_draft=(strategy_a == St.HUMAN_REVIEW))
    print(ans_a)

    print(f"\n{'─'*72}")
    print("  [Mode B 답변]  (similarity-only, strategy=" + strategy_b.value + ")")
    print(f"{'─'*72}")
    ans_b = agent._generate_answer(case, label, conf, ctx_b,
                                   is_draft=(strategy_b == St.HUMAN_REVIEW))
    print(ans_b)

    # ── 간단 diff 요약 ────────────────────────────────────────────
    words_a = set(ans_a.split())
    words_b = set(ans_b.split())
    overlap  = len(words_a & words_b) / max(len(words_a | words_b), 1)
    print(f"\n  [단어 overlap]  {overlap:.0%}  {'(매우 유사)' if overlap > 0.7 else '(차이 있음)'}")


def main():
    print("=== RAG 모드 비교: label-aware vs similarity-only (답변 포함) ===")
    print(f"테스트 케이스: 최대 {N_CASES}개  |  LLM 호출: 케이스당 3회 (분류+답변×2)\n")

    agent = load_agent()
    print("\nAgent 준비 완료\n")

    test_cases = load_json_file(os.path.join(BASE, "test.json"))[:N_CASES]

    for i, case in enumerate(test_cases, 1):
        compare_one(agent, case, i)

    print(f"\n{'═'*72}")
    print("비교 완료")
    print("\n[해석 가이드]")
    print("  단어 overlap 높음(>70%) → 두 모드 답변이 거의 동일 → label 필터 영향 적음")
    print("  단어 overlap 낮음(<50%) → 검색 예시 차이가 답변에도 영향 → mode 선택 중요")
    print("  ⚠️ 표시 많음            → label 분류가 RAG 품질을 제한하고 있음")


if __name__ == "__main__":
    main()
