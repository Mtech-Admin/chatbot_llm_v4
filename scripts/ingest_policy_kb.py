"""
Ingest a pre-built structured JSON knowledge base into the pgvector chunk store.

This script expects the JSON produced by the LLM-assisted KB builder
(build_kb.py / dmrc_hr_knowledge_base.json) with the following schema:

  {
    "metadata": {...},
    "chapters": {
      "A": {
        "chapter_title": "...",
        "summary_chunk": "...",
        "rules": [...],
        "tables": [...],
        "authority_index": [...],
        "office_order_index": [...],
        "cross_references": [...]
      },
      ...
    },
    "master_authority_index": [...],
    "master_oo_index": [...],
    "master_cross_reference": [...],
    "leave_types_complete": {...}   # optional
  }

Each chapter produces:
  chapter_summary  — 1 chunk from summary_chunk
  rule_chunk       — 1 per rule in rules[]
  table_chunk      — 1 per table in tables[]
  authority_chunk  — 1 per chapter (authority_index grouped)
  oo_index         — 1 per chapter (office_order_index grouped)
  cross_ref        — 1 per chapter (cross_references grouped)

Master indexes produce additional cross-chapter chunks.

Usage:
  PYTHONPATH=. python scripts/ingest_policy_kb.py \\
      --file /tmp/dmrc_hr_knowledge_base.json \\
      --document-key dmrc_hr_compendium_nov23 \\
      --title "DMRC HR Compendium November 2023" \\
      --replace
"""

from __future__ import annotations

import argparse
import logging
from collections import Counter
from pathlib import Path

from app.knowledge.ingest import read_policy_kb_json_chunks
from app.knowledge.store import policy_store

logger = logging.getLogger(__name__)


def _default_document_key(file_path: Path) -> str:
    return file_path.stem.lower().replace(" ", "_").replace("-", "_")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest structured JSON knowledge base into pgvector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--file", required=True,
        help="Path to the JSON knowledge-base file (e.g. /tmp/dmrc_hr_knowledge_base.json)",
    )
    parser.add_argument(
        "--document-key", default="",
        help="Unique key for this document in the DB (default: derived from filename)",
    )
    parser.add_argument(
        "--title", default="",
        help="Human-readable document title",
    )
    parser.add_argument(
        "--version", default="",
        help="Optional version tag (e.g. NOV23)",
    )
    parser.add_argument(
        "--replace", action="store_true",
        help="Delete existing chunks for this document_key before ingesting",
    )
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if file_path.suffix.lower() != ".json":
        raise ValueError("This script only accepts .json files. For PDF use ingest_policy_pdf.py")

    document_key = (args.document_key or "").strip() or _default_document_key(file_path)
    title = (args.title or "").strip() or file_path.stem
    version = (args.version or "").strip() or None

    print(f"Parsing JSON knowledge base: {file_path}")
    print(f"  document_key : {document_key}")
    print(f"  title        : {title}")

    chunks = read_policy_kb_json_chunks(file_path)

    if not chunks:
        raise RuntimeError("No chunks were produced from the knowledge base JSON.")

    # Print breakdown before storing
    type_counts: Counter[str] = Counter(c.chunk_type for c in chunks)
    chapter_counts: Counter[str] = Counter(c.chapter for c in chunks if c.chapter)

    print(f"\nExtracted {len(chunks)} chunks:")
    for ctype, count in sorted(type_counts.items()):
        print(f"  {ctype:<22} {count:>4}")
    print(f"\nChunks per chapter: {dict(sorted(chapter_counts.items()))}")

    # Flush structured metadata into the .metadata dict for persistence
    for chunk in chunks:
        chunk.metadata = chunk.to_metadata_dict()

    print(f"\nStoring into pgvector (replace={args.replace}) ...")
    result = policy_store.upsert_policy_document(
        document_key=document_key,
        title=title,
        source_file=file_path.name,
        chunks=chunks,
        version=version,
        replace_existing=args.replace,
        metadata={
            "ingest_source": "cli_kb_json",
            "file_path": str(file_path),
            "chunk_type_distribution": dict(type_counts),
            "chapters_ingested": sorted(chapter_counts.keys()),
        },
    )

    print(
        f"\nIngestion complete.\n"
        f"  document_key  : {document_key}\n"
        f"  chunks_read   : {len(chunks)}\n"
        f"  chunks_saved  : {result['chunk_count']}\n"
        f"  document_id   : {result['document_id']}"
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    main()
