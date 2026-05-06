"""
Evaluate policy retrieval quality using a local query set.

Usage:
  PYTHONPATH=. python scripts/evaluate_policy_rag.py --file data/policy_eval_set.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.knowledge.store import policy_store


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def _contains_any_keywords(text: str, keywords: list[str]) -> bool:
    body = _normalize(text)
    return any(_normalize(keyword) in body for keyword in keywords)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate policy RAG retrieval quality")
    parser.add_argument("--file", default="data/policy_eval_set.json", help="Path to eval set JSON")
    parser.add_argument("--top-k", type=int, default=5, help="Top-k chunk retrieval")
    parser.add_argument("--min-combined", type=float, default=0.26, help="Confidence threshold")
    args = parser.parse_args()

    eval_file = Path(args.file).expanduser().resolve()
    if not eval_file.exists():
        raise FileNotFoundError(f"Eval file not found: {eval_file}")

    cases: list[dict[str, Any]] = json.loads(eval_file.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        raise ValueError("Eval file must contain a JSON list")

    total = len(cases)
    if total == 0:
        raise ValueError("Eval file is empty")

    retrieval_hits = 0
    confident_hits = 0
    rows: list[dict[str, Any]] = []
    for case in cases:
        question = str(case.get("question", "")).strip()
        expected_keywords = [str(k) for k in (case.get("expected_keywords") or [])]
        chunks = policy_store.search_chunks(question, top_k=max(1, args.top_k))
        top = chunks[0] if chunks else None
        hit = False
        if chunks and expected_keywords:
            hit = any(_contains_any_keywords(chunk.content, expected_keywords) for chunk in chunks)
        elif chunks:
            hit = True

        if hit:
            retrieval_hits += 1
        if top and top.combined_score >= args.min_combined:
            confident_hits += 1

        rows.append(
            {
                "id": case.get("id"),
                "question": question,
                "expected_keywords": expected_keywords,
                "hit": hit,
                "top_combined_score": round(top.combined_score, 4) if top else 0.0,
                "top_section_title": top.section_title if top else None,
                "top_source_file": top.source_file if top else None,
            }
        )

    result = {
        "total_cases": total,
        "retrieval_hit_rate": round(retrieval_hits / total, 4),
        "confident_rate": round(confident_hits / total, 4),
        "threshold": args.min_combined,
        "cases": rows,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
