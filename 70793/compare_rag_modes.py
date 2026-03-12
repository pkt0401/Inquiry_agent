"""
RAG 검색 모드 비교 (답변 생성 포함)

Mode A — label-aware  : 동일 label 우선, label=None 보조
Mode B — similarity   : label 무시, 순수 유사도 상위 3개

각 테스트 문의에 대해:
  1. 질문 (title + content)
  2. 실제 답변 (운영자 실제 답변)
  3. Mode A 답변 (label-aware RAG)
  4. Mode B 답변 (similarity-only RAG)
  → 결과를 화면 출력 + JSON 파일 저장

실행: python compare_rag_modes.py [테스트케이스수=10] [random_state=42]
"""

import json
import os
import random
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from inquiry_agent import (
    InquiryAgent, load_json_file, _load_dotenv,
    html_to_text, Strategy, RAG_CONFIDENCE_THRESHOLD,
)

ADMIN_IDS = {2, 7, 61, 442, 2425}

N_CASES      = int(sys.argv[1]) if len(sys.argv) > 1 else 10
RANDOM_STATE = int(sys.argv[2]) if len(sys.argv) > 2 else 42


def build_actual_answer_map(comments: list) -> dict:
    """inquiry_id → 운영자 첫 번째 답변 텍스트 매핑"""
    answer_map = {}
    for c in comments:
        qid = c.get("inquiry_id")
        is_admin = c.get("is_admin") or c.get("author_id") in ADMIN_IDS
        if qid and is_admin and qid not in answer_map:
            answer_map[qid] = html_to_text(c.get("content", ""))
    return answer_map


def load_agent():
    _load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[오류] OPENAI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)

    agent = InquiryAgent(api_key=api_key)
    all_inquiries = load_json_file(os.path.join(BASE, "inquiry_all.json"))
    all_comments  = load_json_file(os.path.join(BASE, "inquiry_comment_all.json"))

    actual_answer_map = build_actual_answer_map(all_comments)
    agent.load_inquiry_history(all_inquiries, all_comments, pre_label=True)
    return agent, all_inquiries, actual_answer_map


def sample_test_cases(all_inquiries: list, n: int, seed: int) -> list:
    """전체 문의에서 random_state 고정 후 n개 샘플링."""
    rng = random.Random(seed)
    pool = list(all_inquiries)
    return rng.sample(pool, min(n, len(pool)))


def print_hits(hits: list, mode_name: str):
    print(f"  [{mode_name}] 검색된 예시:")
    if not hits:
        print("    (없음)")
        return
    for i, h in enumerate(hits, 1):
        lbl   = (h.get("label") or "None")[:22]
        title = h.get("title", "")[:45]
        print(f"    {i}. score={h['score']:.3f} | {h.get('type','?'):<14} | label={lbl:<22} | {title}")


def compare_one(agent: InquiryAgent, case: dict, idx: int, actual_answer_map: dict) -> dict:
    title        = case.get("title", "")
    content      = html_to_text(case.get("content", ""))
    qid          = case.get("id")
    inquiry_text = title + " " + content
    actual_ans   = actual_answer_map.get(qid, "(실제 답변 없음)")

    print(f"\n{'═'*72}")
    print(f"테스트 {idx}: {title}")
    print(f"{'═'*72}")

    # 질문
    preview = content[:300].replace('\n', ' ').strip()
    print(f"  [질문]\n  {preview}{'...' if len(content) > 300 else ''}")

    # 실제 답변
    actual_preview = actual_ans[:300].replace('\n', ' ').strip()
    print(f"\n  [실제 답변]\n  {actual_preview}{'...' if len(actual_ans) > 300 else ''}")

    # ── Step 1: LLM 분류 ──────────────────────────────────────────
    clf   = agent._llm_classify(case)
    label = clf.label
    conf  = clf.confidence_level
    print(f"\n  [LLM 분류]  label={label.value}  /  confidence={conf.value}")
    if clf.is_compound:
        print(f"  [복합 문의]  sub_labels={clf.sub_labels}")
    print(f"  [근거]      {clf.rationale}")

    # ── Mode A: label-aware ────────────────────────────────────────
    ctx_a, score_a = agent._build_kb_context(label, inquiry_text, similarity_only=False)
    hits_a = agent.vector_store.search(inquiry_text, label=label.value, top_k=3, similarity_only=False)

    # ── Mode B: similarity-only ────────────────────────────────────
    ctx_b, score_b = agent._build_kb_context(label, inquiry_text, similarity_only=True)
    hits_b = agent.vector_store.search(inquiry_text, label=label.value, top_k=3, similarity_only=True)

    # 검색 예시 비교
    print()
    print_hits(hits_a, "Mode A  label-aware ")
    print_hits(hits_b, "Mode B  similarity  ")

    diff = score_b - score_a
    if diff > 0.05:
        print(f"\n  ⚠️  B가 더 높은 유사도 문서 확보 (차이: {diff:+.3f})")
    else:
        print(f"\n  ✅  A가 충분한 유사도로 label 문서 확보 (A={score_a:.3f}, B={score_b:.3f})")

    # ── strategy 결정 ─────────────────────────────────────────────
    base_strategy, should_respond = agent._determine_strategy(label, conf, clf)

    if not should_respond:
        print("\n  → NO_RESPONSE: 두 모드 모두 답변 생성 안 함")
        return {
            "idx": idx, "id": qid, "title": title, "content": content,
            "actual_answer": actual_ans,
            "label": label.value, "confidence": conf.value,
            "is_compound": clf.is_compound, "sub_labels": clf.sub_labels,
            "rationale": clf.rationale,
            "strategy": "no_response",
            "mode_a": None, "mode_b": None,
        }

    strategy_a = (Strategy.HUMAN_REVIEW
                  if base_strategy == Strategy.TOOL_RAG and score_a < RAG_CONFIDENCE_THRESHOLD
                  else base_strategy)
    strategy_b = (Strategy.HUMAN_REVIEW
                  if base_strategy == Strategy.TOOL_RAG and score_b < RAG_CONFIDENCE_THRESHOLD
                  else base_strategy)

    # ── Mode A 답변 ────────────────────────────────────────────────
    print(f"\n{'─'*72}")
    print(f"  [Mode A 답변]  label-aware  |  strategy={strategy_a.value}")
    print(f"{'─'*72}")
    ans_a = agent._generate_answer(case, label, conf, ctx_a,
                                   is_draft=(strategy_a == Strategy.HUMAN_REVIEW))
    print(ans_a)

    # ── Mode B 답변 ────────────────────────────────────────────────
    print(f"\n{'─'*72}")
    print(f"  [Mode B 답변]  similarity-only  |  strategy={strategy_b.value}")
    print(f"{'─'*72}")
    ans_b = agent._generate_answer(case, label, conf, ctx_b,
                                   is_draft=(strategy_b == Strategy.HUMAN_REVIEW))
    print(ans_b)

    words_a = set(ans_a.split())
    words_b = set(ans_b.split())
    overlap  = len(words_a & words_b) / max(len(words_a | words_b), 1)
    print(f"\n  [단어 overlap]  {overlap:.0%}  {'(매우 유사)' if overlap > 0.7 else '(차이 있음)'}")

    return {
        "idx": idx,
        "id": qid,
        "title": title,
        "content": content,
        "actual_answer": actual_ans,
        "label": label.value,
        "confidence": conf.value,
        "is_compound": clf.is_compound,
        "sub_labels": clf.sub_labels,
        "rationale": clf.rationale,
        "strategy_base": base_strategy.value,
        "mode_a": {
            "strategy": strategy_a.value,
            "rag_score": round(score_a, 4),
            "answer": ans_a,
        },
        "mode_b": {
            "strategy": strategy_b.value,
            "rag_score": round(score_b, 4),
            "answer": ans_b,
        },
        "word_overlap": round(overlap, 3),
    }


def main():
    print("=== RAG 모드 비교: label-aware vs similarity-only ===")
    print(f"테스트 케이스: {N_CASES}개  |  random_state={RANDOM_STATE}  |  LLM 호출: 케이스당 3회\n")

    agent, all_inquiries, actual_answer_map = load_agent()
    print(f"\nAgent 준비 완료  |  전체 문의: {len(all_inquiries)}건  |  실제 답변 매핑: {len(actual_answer_map)}건\n")

    test_cases = sample_test_cases(all_inquiries, N_CASES, RANDOM_STATE)
    print(f"샘플링 완료: {len(test_cases)}건 (random_state={RANDOM_STATE})\n")

    results = []
    for i, case in enumerate(test_cases, 1):
        result = compare_one(agent, case, i, actual_answer_map)
        results.append(result)

    # JSON 저장
    out_path = os.path.join(BASE, f"compare_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'═'*72}")
    print(f"비교 완료  →  결과 저장: {out_path}")
    print("\n[해석 가이드]")
    print("  단어 overlap 높음(>70%) → 두 모드 답변이 거의 동일 → label 필터 영향 적음")
    print("  단어 overlap 낮음(<50%) → 검색 예시 차이가 답변에도 영향 → mode 선택 중요")
    print("  ⚠️ 표시 많음            → label 분류가 RAG 품질을 제한하고 있음")


if __name__ == "__main__":
    main()
