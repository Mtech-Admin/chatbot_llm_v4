"""API models for persisted chat history."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChatHistoryItem(BaseModel):
    id: int
    emp_id: str
    user_message: str
    bot_response: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    items: List[ChatHistoryItem]
    total: int = Field(description="Total rows for this employee (all pages)")
    limit: int
    offset: int


# --- GET /v1/chat/history (HS256 + query pagination) ---


class ChatHistoryV1Item(BaseModel):
    id: int
    user_message: str
    bot_response: str
    created_at: Optional[str] = None


class ChatHistoryV1Response(BaseModel):
    status: Literal["success"] = "success"
    total_count: int
    current_page: int
    page_size: int
    history: List[ChatHistoryV1Item]
