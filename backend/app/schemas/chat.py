"""
backend/app/schemas/chat.py

Request/response shapes for the chat endpoint. This is the contract
between the API and any client (terminal chat now, React frontend later).

Each request is independent — no conversation history yet. A
conversation_id can be added later as an optional field without
breaking existing clients.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from pydantic import BaseModel, model_validator

class ChatRequest(BaseModel):
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