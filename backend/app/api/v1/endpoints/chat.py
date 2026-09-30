"""
backend/app/api/v1/endpoints/chat.py

POST /api/v1/chat — ask a question, get an answer plus its sources.

Request/response shapes live in backend/app/schemas/chat.py (imported
below — do not redeclare them here, or the two copies will drift apart).

Error mapping:
  * Gemini overloaded / unreachable -> 503 + Retry-After (client may retry)
  * Gemini credentials rejected     -> 500, generic message (real cause is
                                       logged, not sent to the client)
  * anything else                   -> FastAPI's default 500; the traceback
                                       is logged and no internals leak
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.conversation import Conversation
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.rag.pipeline import (
    LLMConfigError,
    LLMUnavailableError,
    RagPipeline,
)

logger = logging.getLogger(__name__)

router = APIRouter()

BUSY_MESSAGE = (
    "የመልስ አገልግሎቱ ለጊዜው በጣም ተጨናንቋል። "
    "እባክዎ ከጥቂት ሰከንዶች በኋላ ጥያቄዎን እንደገና ይሞክሩ።"
)
RETRY_AFTER_SECONDS = "10"


@router.post("", response_model=ChatResponse)
def ask_question(payload: ChatRequest, request: Request) -> ChatResponse:
    pipeline: RagPipeline = request.app.state.rag_pipeline

    try:
        result = pipeline.answer(
            query=payload.question,
            top_k=payload.top_k or 5,
            case_number=payload.case_number,
            volume=payload.volume,
            legal_category=payload.legal_category,
        )
        
    except LLMUnavailableError as e:
        logger.warning("Chat request failed, Gemini unavailable: %s", e)
        raise HTTPException(
            status_code=503,
            detail=BUSY_MESSAGE,
            headers={"Retry-After": RETRY_AFTER_SECONDS},
        )
    except LLMConfigError as e:
        logger.error("Gemini configuration problem: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Server configuration error. Please contact the administrator.",
        )

    return ChatResponse(**result)
@router.get("/conversations")
def get_conversations(db: Session = Depends(get_db)):
    """Fetch all past conversations for the frontend sidebar."""
    # Queries the SQLite chat_history.db for all conversations, newest first
    conversations = db.query(Conversation).order_by(Conversation.created_at.desc()).all()
    return conversations