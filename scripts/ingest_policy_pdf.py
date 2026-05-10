"""
Ingest a structured policy PDF (e.g. DMRC HR Compendium) into the pgvector chunk store.

The parser extracts semantically typed chunks:
  chapter_summary  — one per chapter (A–M)
  rule_chunk       — numbered rule blocks (e.g. "3.1 CASUAL LEAVE")
  table_chunk      — extracted tables serialised as JSON
  authority_chunk  — sanction/approval authority paragraphs
  oo_index         — paragraphs carrying O.O. / Office Order references
  cross_ref        — cross-chapter reference paragraphs

Usage:
  PYTHONPATH=. ./.venv/bin/python scripts/ingest_policy_pdf.py \\
      --file "/path/to/Updated_HR_Compendium_-NOV23.pdf" \\
      --document-key "dmrc_hr_compendium_nov23" \\
      --title "DMRC HR Compendium November 2023" \\
      --replace
"""

from __future__ import annotations

import argparse
import logging
from collections import Counter
from pathlib import Path

from app.knowledge.ingest import read_policy_pdf_chunks
from app.knowledge.store import policy_store

logger = logging.getLogger(__name__)


def _default_document_key(file_path: Path) -> str:
    return file_path.stem.lower().replace(" ", "_").replace("-", "_")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest structured policy PDF for RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--file", required=True, help="Absolute path to .pdf file")
    parser.add_argument(
        "--document-key",
        default="",
        help="Unique key for this policy document (default: derived from filename)",
    )
    parser.add_argument("--title", default="", help="Display title for this policy document")
    parser.add_argument("--version", default="", help="Optional document version tag (e.g. NOV23)")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing chunks for the same document_key",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1800,
        help="Target chunk size in characters (default: 1800)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Chunk overlap in characters (default: 200)",
    )
    parser.add_argument(
        "--min-chunk",
        type=int,
        default=150,
        help="Minimum chunk size to keep (default: 150)",
    )
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Only .pdf files are supported by this script. For .docx use ingest_policy_docx.py")

    document_key = (args.document_key or "").strip() or _default_document_key(file_path)
    title = (args.title or "").strip() or file_path.stem
    version = (args.version or "").strip() or None

    print(f"Parsing PDF: {file_path}")
    print(f"  document_key : {document_key}")
    print(f"  title        : {title}")
    print(f"  chunk_size   : {args.chunk_size} chars  overlap={args.chunk_overlap}")

    chunks = read_policy_pdf_chunks(
        file_path,
        chunk_size_chars=args.chunk_size,
        chunk_overlap_chars=args.chunk_overlap,
        min_chunk_chars=args.min_chunk,
    )

    if not chunks:
        raise RuntimeError("No chunks were extracted from the PDF — check that the file is text-based (not scanned).")

    # Print chunk-type breakdown before storing
    type_counts: Counter[str] = Counter(c.chunk_type for c in chunks)
    chapter_counts: Counter[str] = Counter(c.chapter for c in chunks if c.chapter)
    print(f"\nExtracted {len(chunks)} chunks:")
    for ctype, count in sorted(type_counts.items()):
        print(f"  {ctype:<20} {count:>5}")
    print(f"\nChunks per chapter: {dict(sorted(chapter_counts.items()))}")

    # Merge structured metadata into the .metadata dict so store.py persists it
    for chunk in chunks:
        chunk.metadata = chunk.to_metadata_dict()

    print(f"\nStoring chunks into pgvector (replace={args.replace}) ...")
    result = policy_store.upsert_policy_document(
        document_key=document_key,
        title=title,
        source_file=file_path.name,
        chunks=chunks,
        version=version,
        replace_existing=args.replace,
        metadata={
            "ingest_source": "cli_pdf",
            "chunk_size_chars": args.chunk_size,
            "chunk_overlap_chars": args.chunk_overlap,
            "file_path": str(file_path),
            "chunk_type_distribution": dict(type_counts),
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
