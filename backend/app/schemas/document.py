"""
backend/app/schemas/document.py

Pydantic models for document ingestion inputs and outputs.
"""
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str  # "processing" | "indexed" | "failed"
    chunks: int


class DocumentSummary(BaseModel):
    """One row in GET /documents — matches Document.to_dict() in
    models/conversation.py."""
    document_id: str
    filename: str
    status: str
    chunks: int
    uploaded_at: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]