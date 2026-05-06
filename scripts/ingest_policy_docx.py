"""
Ingest long-form policy DOCX into pgvector-backed policy chunk store.

Usage:
  PYTHONPATH=. ./.venv/bin/python scripts/ingest_policy_docx.py \
      --file "/path/to/policy.docx" \
      --document-key "dmrc_policy_2026" \
      --title "DMRC HR Policy 2026"
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.knowledge.ingest import read_policy_docx_chunks
from app.knowledge.store import policy_store

logger = logging.getLogger(__name__)


def _default_document_key(file_path: Path) -> str:
    return file_path.stem.lower().replace(" ", "_")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest policy DOCX for RAG")
    parser.add_argument("--file", required=True, help="Absolute path to .docx file")
    parser.add_argument("--document-key", default="", help="Unique key for this policy document")
    parser.add_argument("--title", default="", help="Display title for this policy document")
    parser.add_argument("--version", default="", help="Optional document version tag (e.g. 2026.1)")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing chunks for the same document_key",
    )
    parser.add_argument("--chunk-size", type=int, default=2200, help="Chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=300, help="Chunk overlap in characters")
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if file_path.suffix.lower() != ".docx":
        raise ValueError("Only .docx is supported for this script")

    document_key = (args.document_key or "").strip() or _default_document_key(file_path)
    title = (args.title or "").strip() or file_path.stem
    version = (args.version or "").strip() or None

    chunks = read_policy_docx_chunks(
        file_path,
        chunk_size_chars=args.chunk_size,
        chunk_overlap_chars=args.chunk_overlap,
    )
    if not chunks:
        raise RuntimeError("No text chunks were extracted from DOCX")

    result = policy_store.upsert_policy_document(
        document_key=document_key,
        title=title,
        source_file=file_path.name,
        chunks=chunks,
        version=version,
        replace_existing=args.replace,
        metadata={
            "ingest_source": "cli",
            "chunk_size_chars": args.chunk_size,
            "chunk_overlap_chars": args.chunk_overlap,
            "file_path": str(file_path),
        },
    )
    print(
        "DOCX ingestion complete. "
        f"document_key={document_key}, chunks_read={len(chunks)}, chunks_saved={result['chunk_count']}"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
