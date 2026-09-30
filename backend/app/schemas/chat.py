"""
backend/app/schemas/chat.py

Pydantic validation schemas for chat requests, responses, and history.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from pydantic import BaseModel, model_validator

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
    question: Optional[str] = None
    message: Optional[str] = None
    prompt: Optional[str] = None
    query: Optional[str] = None  # Add this line so FastAPI accepts the 'query' key
    conversation_id: Optional[str] = None  # Add this since the frontend is sending it
    case_number: Optional[str] = None
    volume: Optional[int] = None
    legal_category: Optional[str] = None
    top_k: Optional[int] = 5

    @model_validator(mode="after")
    def validate_and_normalize_question(self):
        # Include self.query in the fallback check
        query_text = self.question or self.message or self.prompt or self.query
        if not query_text or not query_text.strip():
            raise ValueError("A question, message, prompt, or query text is required.")
        self.question = query_text.strip()
        return self

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