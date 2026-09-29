"""
backend/app/core/database.py

SQLAlchemy engine + session setup for conversation history. Separate from
Chroma (RAG data) and separate from the future users DB table — this file
only owns the chat_history.db file and its Base/session machinery.

Usage:
    from backend.app.core.database import Base, get_db, init_db

    # once, at app startup (in main.py's lifespan):
    init_db()

    # per-request, as a FastAPI dependency:
    @router.get(...)
    def handler(db: Session = Depends(get_db)):
        ...
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# backend/app/core/database.py -> parents[2] is backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BACKEND_DIR / "data" / "chat_history.db"

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

# check_same_thread=False is required for SQLite + FastAPI: FastAPI can
# serve one request's DB calls from a different thread than the one that
# opened the connection. This is safe here because each request gets its
# own Session (see get_db below) — connections are never shared across
# requests/threads at the same time.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """All ORM models (Conversation, Message, and later User) inherit
    from this so init_db() can create every table in one call."""
    pass


def get_db():
    """FastAPI dependency: yields one Session per request, always closed
    afterward even if the request raised an exception."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables that don't exist yet. Safe to call on every
    startup — existing tables/data are left untouched. Must be called
    AFTER every module defining a model (conversation.py, user.py) has
    been imported at least once, or SQLAlchemy won't know about their
    tables yet.
    """
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
