from backend.app.models import conversation  # import so init_db() sees its tables
from backend.app.core.database import init_db
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.app.services.rag.embeddings import EmbeddingClient
from backend.app.services.rag.pipeline import RagPipeline
from backend.app.services.rag.retriever import Retriever
from backend.app.services.rag.vector_store import ChromaVectorStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading embedder + vector store (one-time)...")
    embedder = EmbeddingClient()
    store = ChromaVectorStore(
        db_dir="backend/data/vector_db",
        collection_name="volume_15",
    )
    print(f"  -> vector store has {store.count()} chunks")
    app.state.rag_pipeline = RagPipeline(Retriever(embedder, store))
    yield


app = FastAPI(title="Ethiopian Cassation RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

init_db()
