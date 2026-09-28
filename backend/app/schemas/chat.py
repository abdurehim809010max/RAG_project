"""
backend/app/schemas/chat.py

Request/response shapes for the chat endpoint. This is the contract
between the API and any client (terminal chat now, React frontend later).

Each request is independent — no conversation history yet. A
conversation_id can be added later as an optional field without
breaking existing clients.
"""

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, description="The user's question, in Amharic.")

    # Optional scoping. If case_number is given, retrieval is limited to
    # that case. Otherwise the retriever falls back to its own
    # auto-detection from the question text.
    case_number: str | None = Field(
        default=None,
        pattern=r"^\d{4,6}$",
        description="Restrict the search to one case, e.g. '80343'.",
    )
    volume: int | None = Field(default=None, ge=1, description="Restrict to one volume, e.g. 15.")
    legal_category: str | None = None

    # None means "use the server default from settings".
    top_k: int | None = Field(default=None, ge=1, le=20)


class Source(BaseModel):
    case_number: str
    page_range: str
    legal_category: str
    chunk_id: str
    distance: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]