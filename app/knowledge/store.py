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
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, create_engine, func, or_
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base

from app.config import settings
from app.knowledge.ingest import CHUNK_TYPE_FAQ, PolicyDocChunk, deduplicate_faq_rows

logger = logging.getLogger(__name__)
Base = declarative_base()

_EMBEDDING_MODEL = None
_EMBEDDING_MODEL_LOAD_FAILED = False
_DOC_EMBEDDING_DIM = 384  # all-MiniLM-L6-v2
_LEXICAL_STOPWORDS = {
    "about",
    "above",
    "after",
    "again",
    "against",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "now",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "please",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "with",
    "would",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
}


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

    def upsert_faq_as_chunks(
        self,
        entries: list[dict[str, Any]],
        *,
        document_key: str = "faq_kb",
        document_title: str = "FAQ Knowledge Base",
        source_file: str = "faq_kb",
        replace_existing: bool = True,
    ) -> dict[str, Any]:
        """
        Ingest FAQ Q&A pairs as PolicyChunk rows inside a virtual FAQ document.

        Each entry must contain 'question' and 'answer' keys.  The chunk content
        is stored as "Question: {q}\\nAnswer: {a}" so the same pgvector index and
        hybrid search covers both FAQ and policy-document chunks in one query.

        Returns the same shape as upsert_policy_document().
        """
        if not entries:
            return {"document_id": -1, "document_key": document_key, "chunk_count": 0}

        entries, removed = deduplicate_faq_rows(entries)
        if removed:
            logger.info(
                "upsert_faq_as_chunks: removed %s duplicate FAQ row(s) before ingestion (document_key=%s)",
                removed,
                document_key,
            )

        chunks: list[PolicyDocChunk] = []
        for idx, entry in enumerate(entries):
            question = str(entry.get("question", "")).strip()
            answer = str(entry.get("answer", "")).strip()
            if not question or not answer:
                continue
            content = f"Question: {question}\nAnswer: {answer}"
            chunks.append(
                PolicyDocChunk(
                    chunk_index=idx,
                    content=content,
                    chunk_type=CHUNK_TYPE_FAQ,
                    section_title=question[:120],
                    metadata={
                        "chunk_type": CHUNK_TYPE_FAQ,
                        "question": question,
                        "answer": answer,
                        "source_file": source_file,
                        "row_number": entry.get("row_number"),
                    },
                )
            )

        if not chunks:
            return {"document_id": -1, "document_key": document_key, "chunk_count": 0}

        return self.upsert_policy_document(
            document_key=document_key,
            title=document_title,
            source_file=source_file,
            chunks=chunks,
            replace_existing=replace_existing,
            metadata={"ingest_source": "faq", "faq_count": len(chunks)},
        )

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
                # Use to_metadata_dict() if available (structured PDF chunks) so that
                # chunk_type, chapter, rule_number, oo_references etc. are persisted.
                if hasattr(chunk, "to_metadata_dict"):
                    payload_meta = chunk.to_metadata_dict()
                else:
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

    def search_chunks_by_type(
        self,
        query: str,
        chunk_type: str,
        *,
        top_k: int = 5,
        document_key: str | None = None,
        fallback_if_few: int = 2,
    ) -> list[PolicyChunkMatch]:
        """
        Search chunks filtered to a specific chunk_type stored in metadata JSONB.
        Falls back to an unfiltered search when fewer than `fallback_if_few` results
        are returned (e.g. the document has not been ingested with structured metadata).
        """
        results = self.search_chunks(
            query,
            top_k=top_k,
            document_key=document_key,
            chunk_type=chunk_type,
        )
        if len(results) < fallback_if_few:
            logger.debug(
                "chunk_type=%s returned %s results (< %s), falling back to unfiltered search",
                chunk_type,
                len(results),
                fallback_if_few,
            )
            results = self.search_chunks(query, top_k=top_k, document_key=document_key)
        return results

    def search_chunks(
        self,
        query: str,
        *,
        top_k: int = 5,
        document_key: str | None = None,
        chunk_type: str | None = None,
        chunk_types: list[str] | None = None,
        vector_weight: float = 0.85,
        keyword_weight: float = 0.15,
    ) -> list[PolicyChunkMatch]:
        if not query.strip():
            return []

        query_embedding = self._embed_doc_text(query)
        query_terms = self._extract_query_terms(query)
        vector_candidate_limit = max(top_k * 8, 24)
        lexical_candidate_limit = max(top_k * 8, 24)
        with Session(self.engine) as session:
            try:
                distance_expr = PolicyChunk.embedding.cosine_distance(query_embedding)
                vector_rows = (
                    session.query(
                        PolicyChunk,
                        PolicyDocument,
                        (1 - distance_expr).label("vector_score"),
                    )
                    .join(PolicyDocument, PolicyDocument.id == PolicyChunk.document_id)
                    .filter(PolicyDocument.is_active.is_(True))
                )
                if document_key:
                    vector_rows = vector_rows.filter(PolicyDocument.document_key == document_key)
                vector_rows = vector_rows.order_by(distance_expr.asc()).limit(vector_candidate_limit).all()
            except SQLAlchemyError as exc:
                logger.warning("pgvector search failed, using in-memory fallback: %s", str(exc))
                vector_rows = self._fallback_chunk_search(
                    session,
                    query_embedding,
                    document_key,
                    limit=vector_candidate_limit,
                )

            lexical_rows = self._lexical_chunk_candidates(
                session,
                query=query,
                query_terms=query_terms,
                document_key=document_key,
                limit=lexical_candidate_limit,
            )

        candidate_by_chunk_id: dict[int, tuple[PolicyChunk, PolicyDocument, float]] = {}
        for chunk_row, doc_row, vector_score in vector_rows:
            candidate_by_chunk_id[int(chunk_row.id)] = (chunk_row, doc_row, float(vector_score))

        for chunk_row, doc_row in lexical_rows:
            key = int(chunk_row.id)
            if key in candidate_by_chunk_id:
                continue
            emb = chunk_row.embedding
            try:
                # pgvector returns its own ndarray-like type, not a plain list; always coerce.
                vec_list = list(emb) if emb is not None else []
            except Exception:
                vec_list = []
            vector_score = self._cosine_similarity(query_embedding, vec_list)
            candidate_by_chunk_id[key] = (chunk_row, doc_row, float(vector_score))

        ranked: list[PolicyChunkMatch] = []
        for chunk_row, doc_row, vector_score in candidate_by_chunk_id.values():
            kw = self._keyword_overlap(query, chunk_row.content)
            exact_term_bonus = self._exact_term_bonus(query_terms, chunk_row.content)
            combined = (
                vector_weight * float(vector_score)
                + keyword_weight * float(kw)
                + 0.10 * float(exact_term_bonus)
            )
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

        if chunk_type:
            ranked = [
                m for m in ranked
                if (m.metadata or {}).get("chunk_type") == chunk_type
            ]
        elif chunk_types:
            allowed = set(chunk_types)
            ranked = [
                m for m in ranked
                if (m.metadata or {}).get("chunk_type") in allowed
            ]

        return ranked[:top_k]

    def _lexical_chunk_candidates(
        self,
        session: Session,
        *,
        query: str,
        query_terms: list[str],
        document_key: str | None,
        limit: int,
    ) -> list[tuple[PolicyChunk, PolicyDocument]]:
        if not query_terms and not query.strip():
            return []

        q = session.query(PolicyChunk, PolicyDocument).join(PolicyDocument, PolicyDocument.id == PolicyChunk.document_id)
        q = q.filter(PolicyDocument.is_active.is_(True))
        if document_key:
            q = q.filter(PolicyDocument.document_key == document_key)

        filters = []
        phrase = query.strip().lower()
        if len(phrase) >= 5:
            filters.append(func.lower(PolicyChunk.content).like(f"%{phrase}%"))
        for term in query_terms[:8]:
            filters.append(func.lower(PolicyChunk.content).like(f"%{term}%"))

        if filters:
            q = q.filter(or_(*filters))
        else:
            return []

        return q.order_by(PolicyChunk.chunk_index.asc()).limit(limit).all()

    def search_chunks_by_exact_terms(
        self,
        query: str,
        specific_terms: list[str],
        *,
        top_k: int = 5,
        document_key: str | None = None,
    ) -> list[PolicyChunkMatch]:
        """
        Guaranteed direct DB lookup for specific/rare terms regardless of vector ranking.
        All chunks containing ANY of the terms are fetched and re-ranked by combined score.
        """
        if not specific_terms:
            return []

        query_embedding = self._embed_doc_text(query)
        term_filters = [
            func.lower(PolicyChunk.content).like(f"%{t.lower()}%")
            for t in specific_terms
        ]

        with Session(self.engine) as session:
            q = (
                session.query(PolicyChunk, PolicyDocument)
                .join(PolicyDocument, PolicyDocument.id == PolicyChunk.document_id)
                .filter(PolicyDocument.is_active.is_(True))
                .filter(or_(*term_filters))
            )
            if document_key:
                q = q.filter(PolicyDocument.document_key == document_key)
            rows = q.all()

        results: list[PolicyChunkMatch] = []
        for chunk_row, doc_row in rows:
            try:
                vec_list = list(chunk_row.embedding) if chunk_row.embedding is not None else []
            except Exception:
                vec_list = []
            vector_score = self._cosine_similarity(query_embedding, vec_list)
            kw = self._keyword_overlap(query, chunk_row.content)
            term_hits = sum(
                1 for t in specific_terms if t.lower() in (chunk_row.content or "").lower()
            )
            combined = (
                0.70 * vector_score
                + 0.15 * kw
                + 0.15 * (term_hits / max(1, len(specific_terms)))
            )
            results.append(
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
        results.sort(key=lambda m: m.combined_score, reverse=True)
        return results[:top_k]

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
            try:
                vec_list = list(emb) if emb is not None else []
            except Exception:
                vec_list = []
            score = self._cosine_similarity(query_embedding, vec_list)
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
            return self._hash_embedding(text, dim=_DOC_EMBEDDING_DIM)
        try:
            vec = model.encode(text, normalize_embeddings=True)
            out = [float(x) for x in vec.tolist()]
            if len(out) != _DOC_EMBEDDING_DIM:
                logger.warning(
                    "Document embedding dimension mismatch (expected=%s got=%s). Falling back to hash embedding.",
                    _DOC_EMBEDDING_DIM,
                    len(out),
                )
                return self._hash_embedding(text, dim=_DOC_EMBEDDING_DIM)
            return out
        except Exception as exc:
            logger.warning("Document embedding failed, using hash fallback: %s", str(exc))
            return self._hash_embedding(text, dim=_DOC_EMBEDDING_DIM)

    def _embed_text(self, text: str) -> list[float]:
        model = self._get_sentence_transformer()
        if model is not None:
            vec = model.encode(text, normalize_embeddings=True)
            return [float(x) for x in vec.tolist()]

        return self._hash_embedding(text, dim=256)

    def _get_sentence_transformer(self):
        global _EMBEDDING_MODEL
        global _EMBEDDING_MODEL_LOAD_FAILED
        if _EMBEDDING_MODEL is not None:
            return _EMBEDDING_MODEL
        if _EMBEDDING_MODEL_LOAD_FAILED:
            return None
        try:
            from sentence_transformers import SentenceTransformer

            _EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            _EMBEDDING_MODEL_LOAD_FAILED = False
            logger.info("Loaded sentence-transformer model for policy retrieval")
            return _EMBEDDING_MODEL
        except Exception as exc:
            logger.warning("Falling back to hash embeddings: %s", str(exc))
            _EMBEDDING_MODEL = None
            _EMBEDDING_MODEL_LOAD_FAILED = True
            return None

    @staticmethod
    def _hash_embedding(text: str, *, dim: int) -> list[float]:
        tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
        vec = [0.0] * dim
        if not tokens:
            return vec
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:2], "big") % dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

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
    def _extract_query_terms(text: str) -> list[str]:
        terms = []
        for tok in re.findall(r"[a-zA-Z0-9]+", text.lower()):
            if len(tok) < 3:
                continue
            if tok in _LEXICAL_STOPWORDS:
                continue
            terms.append(tok)
        seen: set[str] = set()
        deduped: list[str] = []
        for term in terms:
            if term in seen:
                continue
            deduped.append(term)
            seen.add(term)
        return deduped

    @staticmethod
    def _exact_term_bonus(query_terms: list[str], content: str) -> float:
        if not query_terms:
            return 0.0
        body = content.lower()
        hits = sum(1 for term in query_terms if term in body)
        return min(1.0, hits / max(1, len(query_terms)))

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
