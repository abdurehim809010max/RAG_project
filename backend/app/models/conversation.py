"""
backend/app/models/conversation.py

SQLAlchemy models for chat history: one Conversation has many Messages.
Also includes the Document model, which tracks uploaded source files and
the ids of the chunks they produced in Chroma. There's no separate
models/document.py in this project's file structure, so Document lives
here alongside Conversation/Message rather than as its own file.

    Conversation
      id            str (UUID, primary key)
      title         str | None  — set from the first question, so a
                                   conversation list has something
                                   readable to show instead of a UUID
      created_at    datetime

    Message
      id               int (autoincrement, primary key)
      conversation_id  str  — FK to Conversation.id
      role             str  — "user" or "assistant"
      content          str  — the question text or the generated answer
      sources_json     str | None
                            — for assistant messages: pipeline.answer()'s
                              "sources" list, stored as a JSON string
                              (SQLite has no native JSON/array column, so
                              this is serialized on write and parsed back
                              on read — see to_dict() below)
      created_at       datetime

    Document
      id               str (UUID, primary key)
      filename         str
      status           str  — "processing" | "indexed" | "failed"
      chunk_count      int
      chunk_ids_json   str  — Chroma chunk ids owned by this document,
                              stored as a JSON string so DELETE can remove
                              exactly those chunks and no others
      uploaded_at      datetime
"""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",   # deleting a conversation deletes its messages
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    sources_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def set_sources(self, sources: list[dict] | None) -> None:
        """Serialize pipeline.answer()'s sources list for storage."""
        self.sources_json = json.dumps(sources) if sources else None

    def get_sources(self) -> list[dict]:
        """Deserialize back to a list of dicts (empty list if none stored,
        never None — callers can iterate without a null check)."""
        return json.loads(self.sources_json) if self.sources_json else []

    def to_dict(self) -> dict:
        """Shape used by the history endpoint response / ConversationHistoryResponse."""
        return {
            "role": self.role,
            "content": self.content,
            "sources": self.get_sources(),
            "created_at": self.created_at.isoformat(),
        }


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="processing")  # processing | indexed | failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    def set_chunk_ids(self, chunk_ids: list[str]) -> None:
        """Serialize the Chroma chunk ids produced by this upload."""
        self.chunk_ids_json = json.dumps(chunk_ids)
        self.chunk_count = len(chunk_ids)

    def get_chunk_ids(self) -> list[str]:
        """Deserialize back to a list of chunk ids (empty list if none stored)."""
        return json.loads(self.chunk_ids_json) if self.chunk_ids_json else []

    def to_dict(self) -> dict:
        """Shape used by GET /documents, matching DocumentUploadResponse's fields."""
        return {
            "document_id": self.id,
            "filename": self.filename,
            "status": self.status,
            "chunks": self.chunk_count,
            "uploaded_at": self.uploaded_at.isoformat(),
        }