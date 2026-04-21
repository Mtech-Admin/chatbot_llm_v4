"""
Versioned chat routes (e.g. /v1/chat/history).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.gateway.auth import get_token_from_header, verify_jwt_token
from app.models.chat_history import ChatHistoryItem, ChatHistoryResponse
from app.storage.chatbot_conversations import fetch_conversation_history

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/chat", tags=["chat-v1"])


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    authorization: Optional[str] = Header(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ChatHistoryResponse:
    """
    List persisted user/bot messages for the authenticated employee
    (newest first). Data comes from `chatbot_conversations` in PostgreSQL.
    """
    try:
        jwt_token = get_token_from_header(authorization)
        auth_info = verify_jwt_token(jwt_token)
        employee_id = str(auth_info["employee_id"])

        rows, total = fetch_conversation_history(
            employee_id,
            limit=limit,
            offset=offset,
        )
        items = [ChatHistoryItem(**row) for row in rows]
        return ChatHistoryResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to load chat history: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load chat history",
        )
