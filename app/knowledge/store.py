"""
Policy knowledge store supporting FAQ and long-form policy document retrieval.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from dataclasses import dataclass
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, create_engine, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base

from app.config import settings
from app.knowledge.ingest import PolicyDocChunk

logger = logging.getLogger(__name__)
Base = declarative_base()

_EMBEDDING_MODEL = None
_DOC_EMBEDDING_DIM = 384  # all-MiniLM-L6-v2


class PolicyQA(Base):
    __tablename__ = "policy_qa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    embedding = Column(JSONB, nullable=False)
    source_file = Column(Text, nullable=True)
    row_number = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    document_key = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(Text, nullable=False)
    version = Column(String(64), nullable=True)
    source_file = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    chunk_count = Column(Integer, nullable=False, default=0)
    meta = Column("metadata", JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    document_id = Column(BigInteger, ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    section_title = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)
    char_start = Column(Integer, nullable=False, default=0)
    char_end = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    embedding = Column(Vector(_DOC_EMBEDDING_DIM), nullable=False)
    meta = Column("metadata", JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


@dataclass
class PolicyMatch:
    question: str
    answer: str
    score: float
    source_file: Optional[str] = None
    row_number: Optional[int] = None


@dataclass
class PolicyChunkMatch:
    document_key: str
    document_title: str
    source_file: str
    chunk_index: int
    section_title: Optional[str]
    page_number: Optional[int]
    content: str
    vector_score: float
    keyword_score: float
    combined_score: float
    metadata: dict[str, Any]


class PolicyKnowledgeStore:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self._reembed_lock = False

    def init_schema(self) -> None:
        return None

    def stats(self) -> dict[str, Any]:
        with Session(self.engine) as session:
            qa_rows = session.query(PolicyQA).count()
            qa_sample = session.query(PolicyQA).first()
            doc_count = session.query(PolicyDocument).count()
            chunk_count = session.query(PolicyChunk).count()
            last_doc = (
                session.query(PolicyDocument)
                .order_by(PolicyDocument.updated_at.desc().nullslast())
                .first()
            )
        embedding_dim = len(qa_sample.embedding) if qa_sample and qa_sample.embedding else 0
        backend = "sentence-transformers" if self._get_sentence_transformer() else "hash"
        return {
            "rows": qa_rows,
            "embedding_dim": embedding_dim,
            "embedding_backend": backend,
            "policy_document_count": doc_count,
            "policy_chunk_count": chunk_count,
            "last_document_key": last_doc.document_key if last_doc else None,
            "last_document_title": last_doc.title if last_doc else None,
            "last_document_chunks": last_doc.chunk_count if last_doc else 0,
        }

    def clear(self, *, policy_qa: bool = True, policy_docs: bool = False) -> None:
        with Session(self.engine) as session:
            if policy_docs:
                session.query(PolicyChunk).delete()
                session.query(PolicyDocument).delete()
            if policy_qa:
                session.query(PolicyQA).delete()
            session.commit()

    def upsert_entries(self, entries: list[dict[str, Any]], source_file: Optional[str] = None) -> int:
        with Session(self.engine) as session:
            for entry in entries:
                question = str(entry.get("question", "")).strip()
                answer = str(entry.get("answer", "")).strip()
                if not question or not answer:
                    continue
                embedding = self._embed_text(question)
                row_number = entry.get("row_number")
                existing = None
                if source_file and row_number is not None:
                    existing = (
                        session.query(PolicyQA)
                        .filter(PolicyQA.source_file == source_file, PolicyQA.row_number == row_number)
                        .first()
                    )
                if existing:
                    existing.question = question
                    existing.answer = answer
                    existing.embedding = embedding
                else:
                    session.add(
                        PolicyQA(
                            question=question,
                            answer=answer,
                            embedding=embedding,
                            source_file=source_file,
                            row_number=row_number,
                        )
                    )
            session.commit()
            return session.query(PolicyQA).count()

    def upsert_policy_document(
        self,
        *,
        document_key: str,
        title: str,
        source_file: str,
        chunks: list[PolicyDocChunk],
        version: str | None = None,
        replace_existing: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not document_key.strip():
            raise ValueError("document_key is required")
        if not chunks:
            raise ValueError("chunks are required")

        with Session(self.engine) as session:
            document = session.query(PolicyDocument).filter(PolicyDocument.document_key == document_key).first()
            if document is None:
                document = PolicyDocument(
                    document_key=document_key,
                    title=title,
                    version=version,
                    source_file=source_file,
                    is_active=True,
                    meta=metadata or {},
                )
                session.add(document)
                session.flush()
            else:
                document.title = title
                document.version = version
                document.source_file = source_file
                document.is_active = True
                document.meta = metadata or document.meta or {}
                if replace_existing:
                    session.query(PolicyChunk).filter(PolicyChunk.document_id == document.id).delete()

            for idx, chunk in enumerate(chunks):
                content = chunk.content.strip()
                if not content:
                    continue
                vec = self._embed_doc_text(content)
                payload_meta = dict(chunk.metadata or {})
                session.add(
                    PolicyChunk(
                        document_id=document.id,
                        chunk_index=chunk.chunk_index if chunk.chunk_index is not None else idx,
                        section_title=chunk.section_title,
                        page_number=chunk.page_number,
                        char_start=chunk.char_start,
                        char_end=chunk.char_end,
                        content=content,
                        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        embedding=vec,
                        meta=payload_meta,
                    )
                )

            session.flush()
            chunk_count = session.query(PolicyChunk).filter(PolicyChunk.document_id == document.id).count()
            document.chunk_count = chunk_count
            session.commit()
            return {"document_id": int(document.id), "document_key": document_key, "chunk_count": chunk_count}

    def search(self, query: str, top_k: int = 3) -> list[PolicyMatch]:
        if not query.strip():
            return []

        query_embedding = self._embed_text(query)
        with Session(self.engine) as session:
            rows = session.query(PolicyQA).all()

        if not rows:
            logger.warning("Policy knowledge search: policy_qa table is empty")
            return []

        if rows and isinstance(rows[0].embedding, list) and len(rows[0].embedding) != len(query_embedding):
            logger.warning(
                "Policy embedding dimension mismatch (stored=%s, query=%s). Rebuilding embeddings once.",
                len(rows[0].embedding),
                len(query_embedding),
            )
            self._reembed_all_questions()
            with Session(self.engine) as session:
                rows = session.query(PolicyQA).all()

        matches: list[PolicyMatch] = []
        for row in rows:
            score = self._cosine_similarity(query_embedding, row.embedding)
            matches.append(
                PolicyMatch(
                    question=row.question,
                    answer=row.answer,
                    score=score,
                    source_file=row.source_file,
                    row_number=row.row_number,
                )
            )
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:top_k]

    def search_chunks(
        self,
        query: str,
        *,
        top_k: int = 5,
        document_key: str | None = None,
        vector_weight: float = 0.85,
        keyword_weight: float = 0.15,
    ) -> list[PolicyChunkMatch]:
        if not query.strip():
            return []

        query_embedding = self._embed_doc_text(query)
        with Session(self.engine) as session:
            try:
                distance_expr = PolicyChunk.embedding.cosine_distance(query_embedding)
                rows = (
                    session.query(
                        PolicyChunk,
                        PolicyDocument,
                        (1 - distance_expr).label("vector_score"),
                    )
                    .join(PolicyDocument, PolicyDocument.id == PolicyChunk.document_id)
                    .filter(PolicyDocument.is_active.is_(True))
                )
                if document_key:
                    rows = rows.filter(PolicyDocument.document_key == document_key)
                rows = rows.order_by(distance_expr.asc()).limit(max(top_k * 3, top_k)).all()
            except SQLAlchemyError as exc:
                logger.warning("pgvector search failed, using in-memory fallback: %s", str(exc))
                rows = self._fallback_chunk_search(session, query_embedding, document_key, limit=max(top_k * 3, top_k))

        ranked: list[PolicyChunkMatch] = []
        for chunk_row, doc_row, vector_score in rows:
            kw = self._keyword_overlap(query, chunk_row.content)
            combined = vector_weight * float(vector_score) + keyword_weight * float(kw)
            ranked.append(
                PolicyChunkMatch(
                    document_key=doc_row.document_key,
                    document_title=doc_row.title,
                    source_file=doc_row.source_file,
                    chunk_index=chunk_row.chunk_index,
                    section_title=chunk_row.section_title,
                    page_number=chunk_row.page_number,
                    content=chunk_row.content,
                    vector_score=float(vector_score),
                    keyword_score=float(kw),
                    combined_score=float(combined),
                    metadata=chunk_row.meta or {},
                )
            )

        ranked.sort(key=lambda m: m.combined_score, reverse=True)
        return ranked[:top_k]

    def _fallback_chunk_search(
        self,
        session: Session,
        query_embedding: list[float],
        document_key: str | None,
        *,
        limit: int,
    ) -> list[tuple[PolicyChunk, PolicyDocument, float]]:
        q = session.query(PolicyChunk, PolicyDocument).join(PolicyDocument, PolicyDocument.id == PolicyChunk.document_id)
        q = q.filter(PolicyDocument.is_active.is_(True))
        if document_key:
            q = q.filter(PolicyDocument.document_key == document_key)
        rows = q.limit(max(limit * 3, limit)).all()
        scored: list[tuple[PolicyChunk, PolicyDocument, float]] = []
        for chunk_row, doc_row in rows:
            emb = chunk_row.embedding
            score = self._cosine_similarity(query_embedding, emb if isinstance(emb, list) else [])
            scored.append((chunk_row, doc_row, score))
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:limit]

    def _reembed_all_questions(self) -> None:
        if self._reembed_lock:
            return
        self._reembed_lock = True
        try:
            with Session(self.engine) as session:
                rows = session.query(PolicyQA).all()
                for row in rows:
                    row.embedding = self._embed_text(row.question)
                session.commit()
            logger.info("Rebuilt embeddings for %s policy_qa rows", len(rows))
        finally:
            self._reembed_lock = False

    def _embed_doc_text(self, text: str) -> list[float]:
        model = self._get_sentence_transformer()
        if model is None:
            raise RuntimeError("Sentence-transformers model is required for pgvector document retrieval")
        vec = model.encode(text, normalize_embeddings=True)
        out = [float(x) for x in vec.tolist()]
        if len(out) != _DOC_EMBEDDING_DIM:
            raise RuntimeError(
                f"Embedding dimension mismatch for document retrieval: expected {_DOC_EMBEDDING_DIM}, got {len(out)}"
            )
        return out

    def _embed_text(self, text: str) -> list[float]:
        model = self._get_sentence_transformer()
        if model is not None:
            vec = model.encode(text, normalize_embeddings=True)
            return [float(x) for x in vec.tolist()]

        tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
        dim = 256
        vec = [0.0] * dim
        if not tokens:
            return vec
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:2], "big") % dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def _get_sentence_transformer(self):
        global _EMBEDDING_MODEL
        if _EMBEDDING_MODEL is not None:
            return _EMBEDDING_MODEL
        try:
            from sentence_transformers import SentenceTransformer

            _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded sentence-transformer model for policy retrieval")
            return _EMBEDDING_MODEL
        except Exception as exc:
            logger.warning("Falling back to hash embeddings: %s", str(exc))
            _EMBEDDING_MODEL = None
            return None

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))

    def _keyword_overlap(self, query: str, text: str) -> float:
        q_tokens = self._tokenize(query)
        d_tokens = self._tokenize(text)
        if not q_tokens or not d_tokens:
            return 0.0
        inter = len(q_tokens & d_tokens)
        union = len(q_tokens | d_tokens) or 1
        return inter / union

    @staticmethod
    def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(b * b for b in v2))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)


policy_store = PolicyKnowledgeStore()
