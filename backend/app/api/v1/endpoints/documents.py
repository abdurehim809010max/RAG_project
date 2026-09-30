"""
backend/app/api/v1/endpoints/documents.py

API for uploading and indexing new cassation files.
"""
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from backend.app.services.ingestion.parser import CassationParser
from backend.app.services.rag.chunker import chunk_text
from backend.app.services.rag.embeddings import EmbeddingClient
from backend.app.services.rag.vector_store import ChromaVectorStore
from backend.app.core.config import BACKEND_DIR
from backend.app.services.ingestion.loaders.pdf_loader import CassationPDFLoader
from backend.app.services.ingestion.loaders.docx_loader import DocxLoader
from backend.app.services.ingestion.loaders.text_loader import TextLoader
from backend.app.schemas.document import DocumentUploadResponse


router = APIRouter()

UPLOAD_DIR = BACKEND_DIR / "data" / "raw"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    volume: int = Form(15),
    toc_end_page: int = Form(33)
):
    if not file.filename.endswith(('.txt', '.pdf')):
        raise HTTPException(status_code=400, detail="Only .txt and .pdf files are supported.")
        
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        documents = []
        metadatas = []
        ids = []
        
        embedder = EmbeddingClient()
        vector_store = ChromaVectorStore()

        # 1. Route to the correct loader
        if file.filename.endswith('.pdf'):
            loader = CassationPDFLoader()
            cases = loader.load_and_split(str(file_path), volume_number=volume, toc_end_page=toc_end_page)
        elif file.filename.endswith('.docx'):
            loader = DocxLoader()
            cases = loader.load(str(file_path), volume=volume)
        elif file.filename.endswith('.txt'):
            loader = TextLoader()
            cases = loader.load(str(file_path), volume=volume)
        else:
            raise HTTPException(400, "Unsupported file format.")
            
        # 2. Chunk and prepare for ChromaDB (Same logic for all 3!)
        for case in cases:
            chunk_data = chunk_text(case["context"], chunk_size=800, overlap=150)
            
            for i, (piece, start, end) in enumerate(chunk_data):
                documents.append(piece)
                metadatas.append({
                    "case_number": case["case_number"],
                    "volume": case["volume"],
                    "legal_category": case["legal_category"],
                    "page_range": case["page_range"]
                })
                ids.append(f"{case['case_number']}_{i}")

        # 3. Save to ChromaDB
        if documents:
            embeddings = embedder.encode(documents) # Note: Keep whatever method name worked for you earlier!
            
            vector_store.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            
        return {
            "filename": file.filename,
            "status": "success",
            "chunks_indexed": len(documents),
            "total_cases_found": len(cases) if file.filename.endswith('.pdf') else 1
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))