"""
Hybrid policy retrieval smoke-test with DB coverage checks.

Usage examples:
  PYTHONPATH=. python scripts/test_policy_retrieval_live.py
  PYTHONPATH=. python scripts/test_policy_retrieval_live.py --query "paternity leave policy" --expect "paternity,leave"
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.knowledge.store import PolicyChunk, policy_store


DEFAULT_CASES = [
    {"name": "paternity_leave", "query": "Please provide paternity leave policy", "expect": ["paternity", "leave"]},
    {"name": "maternity_leave", "query": "How much maternity leave is available", "expect": ["maternity", "leave"]},
    {"name": "ltc_rules", "query": "What are leave travel concession rules", "expect": ["leave", "travel", "concession"]},
]


def _contains_terms(text: str, terms: list[str]) -> bool:
    body = (text or "").lower()
    return any((term or "").lower() in body for term in terms)


def _db_term_count(term: str) -> int:
    with Session(policy_store.engine) as session:
        return (
            session.query(PolicyChunk)
            .filter(func.lower(PolicyChunk.content).like(f"%{term.lower()}%"))
            .count()
        )


def _run_case(query: str, expect_terms: list[str], top_k: int) -> dict[str, Any]:
    chunks = policy_store.search_chunks(query, top_k=top_k)
    top = chunks[0] if chunks else None
    hit = any(_contains_terms(chunk.content, expect_terms) for chunk in chunks) if chunks else False
    return {
        "query": query,
        "expect_terms": expect_terms,
        "db_term_counts": {term: _db_term_count(term) for term in expect_terms},
        "top_k": top_k,
        "retrieval_hit": hit,
        "top_score": round(top.combined_score, 4) if top else 0.0,
        "top_section": top.section_title if top else None,
        "top_source": top.source_file if top else None,
        "top_excerpt": ((top.content or "")[:300] if top else None),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Live test script for policy retrieval quality")
    parser.add_argument("--query", default="", help="Single query to test")
    parser.add_argument(
        "--expect",
        default="",
        help="Comma-separated expected terms (used only with --query), e.g. 'paternity,leave'",
    )
    parser.add_argument("--top-k", type=int, default=8, help="Top-k chunks to evaluate")
    args = parser.parse_args()

    if args.query.strip():
        expect_terms = [t.strip().lower() for t in args.expect.split(",") if t.strip()]
        if not expect_terms:
            raise ValueError("--expect is required when --query is provided")
        cases = [{"name": "custom", "query": args.query.strip(), "expect": expect_terms}]
    else:
        cases = DEFAULT_CASES

    results = []
    for case in cases:
        outcome = _run_case(case["query"], case["expect"], max(1, args.top_k))
        outcome["name"] = case["name"]
        results.append(outcome)

    summary = {
        "policy_stats": policy_store.stats(),
        "cases_total": len(results),
        "cases_passed": sum(1 for r in results if r["retrieval_hit"]),
        "cases_failed": sum(1 for r in results if not r["retrieval_hit"]),
        "results": results,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if summary["cases_failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
