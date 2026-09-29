"""
backend/app/schemas/chat.py

Pydantic validation schemas for chat requests, responses, and history.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, description="The user's question in Amharic.")
    conversation_id: str | None = Field(
        default=None,
        description="Optional ID to continue an existing chat session.",
    )
    case_number: str | None = Field(
        default=None,
        pattern=r"^\d{4,6}$",
        description="Restrict the search to one case, e.g. '80343'.",
    )
    volume: int | None = Field(default=None, ge=1, description="Restrict to one volume.")
    legal_category: str | None = None
    top_k: int | None = Field(default=5, ge=1, le=20)


class Source(BaseModel):
    case_number: str
    page_range: str
    legal_category: str
    chunk_id: str
    distance: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    conversation_id: str


# --- New Schemas for Conversation History ---

class MessageResponse(BaseModel):
    role: str
    content: str
    sources: list[Source] | None = None
    created_at: datetime


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    title: str | None
    messages: list[MessageResponse]