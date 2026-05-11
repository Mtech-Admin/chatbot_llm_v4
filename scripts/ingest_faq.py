"""
Ingest FAQ Q&A pairs (CSV or XLSX) into the unified pgvector chunk store.

FAQ entries are stored as PolicyChunk rows under a virtual FAQ document
(document_key = "faq_kb" by default), with chunk_type = "faq_entry".
This means FAQ and policy-document chunks are searched together with a
single hybrid vector+lexical query — no separate score comparison needed.

Usage:
  PYTHONPATH=. python scripts/ingest_faq.py --file data/hr_faq.csv
  PYTHONPATH=. python scripts/ingest_faq.py --file data/hr_faq.xlsx --replace
  PYTHONPATH=. python scripts/ingest_faq.py --file data/hr_faq.csv \\
      --document-key faq_kb --title "DMRC HR FAQ" --replace
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.knowledge.ingest import deduplicate_faq_rows, read_policy_rows
from app.knowledge.store import policy_store

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest FAQ CSV/XLSX into the unified pgvector chunk store",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--file", required=True,
        help="Path to the FAQ CSV or XLSX file",
    )
    parser.add_argument(
        "--document-key", default="faq_kb",
        help="Unique document key for this FAQ set (default: faq_kb)",
    )
    parser.add_argument(
        "--title", default="FAQ Knowledge Base",
        help="Human-readable title for the FAQ document",
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="Delete existing FAQ chunks for this document_key before ingesting",
    )
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    print(f"Reading FAQ file: {file_path}")
    rows = read_policy_rows(file_path)
    print(f"  Found {len(rows)} FAQ rows")

    if not rows:
        print("No rows found — nothing to ingest.")
        return

    rows, removed = deduplicate_faq_rows(rows)
    if removed:
        print(f"  Removed {removed} duplicate row(s) — {len(rows)} unique rows remain")
    else:
        print(f"  No duplicates found")

    print(f"\nIngesting into pgvector (document_key={args.document_key}, replace={args.replace}) ...")
    result = policy_store.upsert_faq_as_chunks(
        rows,
        document_key=args.document_key,
        document_title=args.title,
        source_file=file_path.name,
        replace_existing=args.replace,
    )

    print(
        f"\nIngestion complete.\n"
        f"  document_key  : {result['document_key']}\n"
        f"  document_id   : {result['document_id']}\n"
        f"  rows_read     : {len(rows) + removed}\n"
        f"  duplicates    : {removed}\n"
        f"  chunks_saved  : {result['chunk_count']}"
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    main()
