"""
backend/app/schemas/document.py

Pydantic models for document ingestion inputs and outputs.
"""
from pydantic import BaseModel

class DocumentUploadResponse(BaseModel):
    filename: str
    status: str
    chunks_indexed: int
    total_cases_found: int