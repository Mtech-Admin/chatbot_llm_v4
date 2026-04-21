"""
Policy Q&A knowledge store with lightweight vector retrieval.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import Column, DateTime, Integer, Text, create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session, declarative_base

from app.config import settings

logger = logging.getLogger(__name__)
Base = declarative_base()

_EMBEDDING_MODEL = None


class PolicyQA(Base):
    """Maps to public.policy_qa — created by DMRC_HRMS_API migration CreatePolicyQaTable1776110000000."""

    __tablename__ = "policy_qa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    embedding = Column(JSONB, nullable=False)
    source_file = Column(Text, nullable=True)
    row_number = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


@dataclass
class PolicyMatch:
    question: str
    answer: str
    score: float
    source_file: Optional[str] = None
    row_number: Optional[int] = None


class PolicyKnowledgeStore:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self._reembed_lock = False

    def init_schema(self) -> None:
        """
        Table DDL is applied by DMRC_HRMS_API TypeORM migrations (`policy_qa`).
        Point POSTGRES_* / CHATBOT_DATABASE_URL at the same database as the HRMS API.
        """
        return None

    def stats(self) -> dict[str, Any]:
        with Session(self.engine) as session:
            total = session.query(PolicyQA).count()
            sample = session.query(PolicyQA).first()
        embedding_dim = len(sample.embedding) if sample and sample.embedding else 0
        backend = "sentence-transformers" if self._get_sentence_transformer() else "hash"
        return {
            "rows": total,
            "embedding_dim": embedding_dim,
            "embedding_backend": backend,
        }

    def clear(self) -> None:
        with Session(self.engine) as session:
            session.query(PolicyQA).delete()
            session.commit()

    def upsert_entries(self, entries: List[dict[str, Any]], source_file: Optional[str] = None) -> int:
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
            count = session.query(PolicyQA).count()
            return count

    def search(self, query: str, top_k: int = 3) -> List[PolicyMatch]:
        if not query.strip():
            return []

        query_embedding = self._embed_text(query)
        with Session(self.engine) as session:
            rows = session.execute(select(PolicyQA)).scalars().all()

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
                rows = session.execute(select(PolicyQA)).scalars().all()

        matches: List[PolicyMatch] = []
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
        if matches:
            logger.info(
                "Policy knowledge search: rows=%s top_score=%.4f top_q=%s",
                len(rows),
                matches[0].score,
                matches[0].question[:120],
            )
        return matches[:top_k]

    def _reembed_all_questions(self) -> None:
        if self._reembed_lock:
            return
        self._reembed_lock = True
        try:
            with Session(self.engine) as session:
                rows = session.execute(select(PolicyQA)).scalars().all()
                for row in rows:
                    row.embedding = self._embed_text(row.question)
                session.commit()
            logger.info("Rebuilt embeddings for %s policy_qa rows", len(rows))
        finally:
            self._reembed_lock = False

    def _embed_text(self, text: str) -> list[float]:
        model = self._get_sentence_transformer()
        if model is not None:
            vec = model.encode(text, normalize_embeddings=True)
            return [float(x) for x in vec.tolist()]

        # Fallback deterministic hash embedding (keeps retrieval working offline)
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
