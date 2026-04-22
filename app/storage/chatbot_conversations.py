"""
Persist chat turns to `chatbot_conversations` (HRMS migration table).

See DMRC_HRMS_API migration CreateChatbotConversationsTable1776100000000.
"""

from __future__ import annotations

import logging
from typing import Any, List

from sqlalchemy import Column, DateTime, Integer, String, Text, func, select
from sqlalchemy.orm import Session

from app.knowledge.store import Base
from app.knowledge.store import policy_store

logger = logging.getLogger(__name__)


class ChatbotConversation(Base):
    __tablename__ = "chatbot_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    emp_id = Column(String(255), nullable=False)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


def save_conversation(emp_id: str, user_message: str, bot_response: str) -> None:
    """Insert one user/assistant exchange."""
    uid = (emp_id or "").strip()
    um = (user_message or "").strip()
    br = (bot_response or "").strip()
    if not uid or not um or not br:
        logger.warning("Skipping chatbot_conversations save: empty emp_id or message fields")
        return
    try:
        with Session(policy_store.engine) as session:
            row = ChatbotConversation(
                emp_id=uid,
                user_message=um,
                bot_response=br,
            )
            session.add(row)
            session.commit()
    except Exception as exc:
        logger.error("Failed to persist chatbot_conversations: %s", exc, exc_info=True)
        raise


def fetch_conversation_history(
    emp_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[dict[str, Any]], int]:
    """
    Return rows for one employee, newest first, plus total count for pagination.
    """
    uid = (emp_id or "").strip()
    if not uid:
        return [], 0
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    with Session(policy_store.engine) as session:
        count_q = select(func.count()).select_from(ChatbotConversation).where(
            ChatbotConversation.emp_id == uid
        )
        total = int(session.scalar(count_q) or 0)
        rows = (
            session.execute(
                select(ChatbotConversation)
                .where(ChatbotConversation.emp_id == uid)
                .order_by(ChatbotConversation.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        out: List[dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r.id,
                    "emp_id": r.emp_id,
                    "user_message": r.user_message,
                    "bot_response": r.bot_response,
                    "created_at": r.created_at,
                }
            )
        return out, total


def normalize_history_pagination(page: int, page_size: int) -> tuple[int, int]:
    """
    page defaults to 1 if < 1.
    page_size defaults to 10 if < 1; capped at 50 if > 50.
    """
    p = 1 if page < 1 else page
    if page_size < 1:
        ps = 10
    else:
        ps = min(page_size, 50)
    return p, ps


def fetch_conversation_history_page(
    emp_id: str, page: int, page_size: int
) -> tuple[list[dict[str, Any]], int, int, int]:
    """
    One page of messages for an employee (newest first), plus total row count, normalized page, page_size.
    """
    p, ps = normalize_history_pagination(page, page_size)
    offset = (p - 1) * ps
    rows, total = fetch_conversation_history(emp_id, limit=ps, offset=offset)
    slim: list[dict[str, Any]] = []
    for r in rows:
        ca = r.get("created_at")
        if ca is not None and hasattr(ca, "isoformat"):
            ca_out = ca.isoformat()
        elif ca is not None:
            ca_out = str(ca)
        else:
            ca_out = None
        slim.append(
            {
                "id": r.get("id"),
                "user_message": r.get("user_message", ""),
                "bot_response": r.get("bot_response", ""),
                "created_at": ca_out,
            }
        )
    return slim, total, p, ps
