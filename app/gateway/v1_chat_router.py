"""
Versioned chat routes (e.g. /v1/chat/history).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.gateway.auth import get_token_from_header, verify_jwt_token_history_h256
from app.models.chat_history import ChatHistoryV1Item, ChatHistoryV1Response
from app.storage.chatbot_conversations import fetch_conversation_history_page

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/chat", tags=["chat-v1"])


@router.get("/history", response_model=ChatHistoryV1Response)
async def get_chat_history(
    authorization: Optional[str] = Header(None),
    page: int = Query(1, description="1-based page (values < 1 are treated as 1)"),
    page_size: int = Query(
        10,
        description="Rows per page (default 10; < 1 → 10; > 50 → 50)",
    ),
) -> ChatHistoryV1Response:
    """
    Paginated chat history for the authenticated employee (GET, no body).

    **Auth:** `Authorization: Bearer <JWT>` — HS256, verified with `JWT_SECRET`
    (or `SECRET_KEY` if `JWT_SECRET` is empty). Claims must include `empId` or `emp_id`.

    **Query:** `page` (default 1), `page_size` (default 10, max 50).
    """
    try:
        token = get_token_from_header(authorization)
        auth_info = verify_jwt_token_history_h256(token)
        employee_id = str(auth_info["employee_id"])

        history_rows, total_count, current_page, page_size_out = (
            fetch_conversation_history_page(employee_id, page, page_size)
        )

        history = [ChatHistoryV1Item(**row) for row in history_rows]

        return ChatHistoryV1Response(
            status="success",
            total_count=total_count,
            current_page=current_page,
            page_size=page_size_out,
            history=history,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to load chat history: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load chat history",
        )
