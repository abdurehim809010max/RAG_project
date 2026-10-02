"""
backend/app/api/v1/endpoints/documents.py

API for uploading, listing, and deleting indexed cassation files.
"""
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.config import BACKEND_DIR
from backend.app.core.database import get_db
from backend.app.models.conversation import Document
from backend.app.schemas.document import DocumentUploadResponse
from backend.app.services.ingestion.loaders.docx_loader import DocxLoader
from backend.app.services.ingestion.loaders.pdf_loader import CassationPDFLoader
from backend.app.services.ingestion.loaders.text_loader import TextLoader
from backend.app.services.rag.chunker import chunk_text
from backend.app.services.rag.embeddings import EmbeddingClient
from backend.app.services.rag.vector_store import ChromaVectorStore

router = APIRouter()

UPLOAD_DIR = BACKEND_DIR / "data" / "raw"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    volume: int = Form(15),
    toc_end_page: int = Form(33),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith((".txt", ".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only .txt, .pdf, and .docx files are supported.")

    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc_record = Document(filename=file.filename, status="processing")
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    try:
        documents, metadatas, ids = [], [], []
        embedder = EmbeddingClient()
        vector_store = ChromaVectorStore()

        if file.filename.endswith(".pdf"):
            loader = CassationPDFLoader()
            cases = loader.load_and_split(str(file_path), volume_number=volume, toc_end_page=toc_end_page)
        elif file.filename.endswith(".docx"):
            loader = DocxLoader()
            cases = loader.load(str(file_path), volume=volume)
        else:
            loader = TextLoader()
            cases = loader.load(str(file_path), volume=volume)

        for case_idx, case in enumerate(cases):
                    chunk_data = chunk_text(case["context"], chunk_size=800, overlap=150)
        
                    for i, (piece, start, end) in enumerate(chunk_data):
                        documents.append(piece)
                        metadatas.append({
                            "case_number": case["case_number"],
                            "volume": case["volume"],
                            "legal_category": case["legal_category"],
                            "page_range": case["page_range"],
                            "document_id": doc_record.id,
                        })
                        ids.append(f"{doc_record.id}_{case_idx}_{case['case_number']}_{i}")
        
        if documents:
            embeddings = embedder.embed_passages(documents)
            vector_store.collection.add(
                ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents
            )

        doc_record.status = "indexed"
        doc_record.set_chunk_ids(ids)
        db.commit()

        return doc_record.to_dict()

    except Exception as e:
        doc_record.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return {"documents": [d.to_dict() for d in docs]}


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc_record = db.query(Document).filter(Document.id == document_id).first()
    if not doc_record:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunk_ids = doc_record.get_chunk_ids()
    if chunk_ids:
        vector_store = ChromaVectorStore()
        vector_store.collection.delete(ids=chunk_ids)

    db.delete(doc_record)
    db.commit()