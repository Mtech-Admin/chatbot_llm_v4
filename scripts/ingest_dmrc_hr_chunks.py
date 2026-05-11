"""
Ingest `dmrc_hr_chunks.json` into pgvector using the app embedding stack
(sentence-transformers all-MiniLM-L6-v2, same as policy_store._embed_doc_text).

This replaces ad-hoc PDF/DOCX/KB-json chunking for production policy RAG when you
standardize on the pre-built 124-chunk package.

Usage:
  cd dmrc_chatbot
  PYTHONPATH=. python scripts/ingest_dmrc_hr_chunks.py \\
      --file files/dmrc_hr_chunks.json \\
      --document-key dmrc_hr_compendium_nov23 \\
      --replace

To remove every policy document row first (FAQ policy_qa untouched):
  PYTHONPATH=. python scripts/ingest_dmrc_hr_chunks.py --file files/dmrc_hr_chunks.json --wipe-all-policy-docs

Set in `.env.local`:
  POLICY_RAG_DOCUMENT_KEY=dmrc_hr_compendium_nov23
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.knowledge.ingest import read_dmrc_hr_rag_chunks_json
from app.knowledge.store import policy_store


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest dmrc_hr_chunks.json into pgvector (local embeddings)",
    )
    parser.add_argument(
        "--file",
        default="files/dmrc_hr_chunks.json",
        help="Path to dmrc_hr_chunks.json",
    )
    parser.add_argument(
        "--document-key",
        default="dmrc_hr_compendium_nov23",
        help="policy_documents.document_key (match POLICY_RAG_DOCUMENT_KEY)",
    )
    parser.add_argument(
        "--title",
        default="DMRC HR Compendium (RAG chunks, Nov 2023)",
        help="Human-readable title",
    )
    parser.add_argument(
        "--version",
        default="NOV23",
        help="Optional version tag",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace chunks for this document_key only",
    )
    parser.add_argument(
        "--wipe-all-policy-docs",
        action="store_true",
        help="Delete ALL policy documents and chunks, then ingest (does not touch policy_qa)",
    )
    args = parser.parse_args()

    file_path = Path(args.file).expanduser().resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"Not found: {file_path}")

    if args.wipe_all_policy_docs:
        policy_store.clear(policy_qa=False, policy_docs=True)
        logging.info("Cleared all policy_documents / policy_chunks")

    chunks = read_dmrc_hr_rag_chunks_json(file_path)
    if not chunks:
        raise RuntimeError("No chunks loaded from JSON")

    for c in chunks:
        c.metadata = c.to_metadata_dict()

    result = policy_store.upsert_policy_document(
        document_key=args.document_key.strip(),
        title=args.title.strip(),
        source_file=file_path.name,
        chunks=chunks,
        version=(args.version or "").strip() or None,
        replace_existing=args.replace or args.wipe_all_policy_docs,
        metadata={
            "ingest_source": "dmrc_hr_chunks_json",
            "file_path": str(file_path),
            "total_chunks": len(chunks),
        },
    )

    print(
        f"Ingestion complete.\n"
        f"  document_key : {result['document_key']}\n"
        f"  chunks_saved : {result['chunk_count']}\n"
        f"  document_id  : {result['document_id']}\n"
        f"\nSet POLICY_RAG_DOCUMENT_KEY={result['document_key']} to pin the policy agent to this corpus."
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    main()
