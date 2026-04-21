"""
Ingest policy Q&A from Excel/CSV into policy_qa knowledge store.

Usage:
  PYTHONPATH=. ./.venv/bin/python scripts/ingest_policy_qa.py --file "/path/to/file.xlsx"
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.knowledge.ingest import read_policy_rows
from app.knowledge.store import policy_store

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest policy Q&A from Excel/CSV")
    parser.add_argument("--file", required=True, help="Absolute path to .xlsx or .csv")
    parser.add_argument("--replace", action="store_true", help="Clear existing policy_qa before ingest")
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    rows = read_policy_rows(file_path)
    if args.replace:
        policy_store.clear()
    total = policy_store.upsert_entries(rows, source_file=file_path.name)
    print(f"Ingestion complete. Rows read={len(rows)}, rows in store={total}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
