"""
backend/app/api/v1/endpoints/chat.py

API endpoints for RAG chat and conversation history.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.app.services.rag.embeddings import EmbeddingClient
from backend.app.services.rag.vector_store import ChromaVectorStore
from backend.app.services.rag.retriever import Retriever
from backend.app.core.database import get_db
from backend.app.models.conversation import Conversation, Message
from backend.app.services.rag.pipeline import RagPipeline
from backend.app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse
)

router = APIRouter()

# Dependency to instantiate the RAG pipeline
def get_pipeline():
    """Instantiate the complete RAG pipeline."""
    embedder = EmbeddingClient()
    vector_store = ChromaVectorStore()

    # FIX: Pass BOTH the embedder and the vector store
    retriever = Retriever(embedder=embedder, vector_store=vector_store)

    return RagPipeline(retriever=retriever)

@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    pipeline: RagPipeline = Depends(get_pipeline)
):
    # 1. Handle Conversation Session
    if request.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == request.conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create a new conversation using the first 50 chars of the question as the title
        conv = Conversation(title=request.question[:50])
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 2. Save User Message to DB
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=request.question
    )
    db.add(user_msg)
    db.commit()

    # 3. Generate Answer using your existing RAG Pipeline
    try:
        result = pipeline.answer(
            query=request.question,
            case_number=request.case_number,
            top_k=request.top_k
        )
        answer_text = result["answer"]
        sources = result["sources"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Pipeline error: {str(e)}")

    # 4. Save AI Response and Citations to DB
    ai_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=answer_text,
        sources_json=json.dumps(sources, ensure_ascii=False) if sources else "[]"
    )
    db.add(ai_msg)
    db.commit()

    # 5. Return Response to Frontend
    return ChatResponse(
        answer=answer_text,
        sources=sources,
        conversation_id=conv.id
    )


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db)):
    """List all conversations, most recent first, for the sidebar history."""
    conversations = (
        db.query(Conversation)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return {
        "conversations": [
            {
                "id": c.id,
                "title": c.title or "Legal Inquiry",
                "created_at": c.created_at.isoformat(),
            }
            for c in conversations
        ]
    }


@router.get("/history/{conversation_id}", response_model=ConversationHistoryResponse)
def get_chat_history(conversation_id: str, db: Session = Depends(get_db)):
    """Fetch previous messages for a specific conversation session."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationHistoryResponse(
        conversation_id=conv.id,
        title=conv.title,
        messages=[
            {
                "role": msg.role,
                "content": msg.content,
                "sources": json.loads(msg.sources_json) if getattr(msg, "sources_json", None) else [],
                "created_at": msg.created_at
            }
            for msg in conv.messages
        ]
    )

@router.post("/stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    pipeline: RagPipeline = Depends(get_pipeline)
):
    """Streams the AI answer token-by-token."""

    # 1. Setup DB conversation (Same logic as standard chat)
    if request.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == request.conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = Conversation(title=request.question[:50])
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 2. Save User Message
    user_msg = Message(conversation_id=conv.id, role="user", content=request.question)
    db.add(user_msg)
    db.commit()

    # 3. Create the generator that streams data AND saves the final answer
    def stream_generator():
        full_answer = ""
        sources_data = []

        yield f"data: {json.dumps({'type': 'info', 'conversation_id': conv.id})}\n\n"

        for sse_string in pipeline.answer_stream(
            query=request.question, case_number=request.case_number, top_k=request.top_k
        ):
            yield sse_string

            if "data: " in sse_string:
                try:
                    payload = json.loads(sse_string.replace("data: ", "").strip())
                    if payload["type"] == "text":
                        full_answer += payload["content"]
                    elif payload["type"] == "sources":
                        sources_data = payload["content"]
                except json.JSONDecodeError:
                    pass

        ai_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=full_answer,
            sources_json=json.dumps(sources_data, ensure_ascii=False) if sources_data else "[]"
        )
        db.add(ai_msg)
        db.commit()

    return StreamingResponse(stream_generator(), media_type="text/event-stream")