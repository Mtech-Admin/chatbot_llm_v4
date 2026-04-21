"""API models for persisted chat history."""

from __future__ import annotations

from datetime import datetime
from typing import List

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
