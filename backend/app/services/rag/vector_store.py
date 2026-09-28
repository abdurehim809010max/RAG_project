"""
backend/app/services/rag/vector_store.py

Chroma connector. This is the only file that should know Chroma's API
specifically — retriever.py and pipeline.py call add()/query() and don't
care what's underneath. Swapping to Qdrant/pgvector later means rewriting
this one file, not touching the rest of the RAG pipeline.
"""

import chromadb


class ChromaVectorStore:
    def __init__(self, db_dir: str = "backend/data/vector_db",
                 collection_name: str = "volume_15"):
        self.client = chromadb.PersistentClient(path=db_dir)
        self.collection_name = collection_name
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self):
        """Delete and recreate the collection. Call this whenever the
        underlying chunks change (re-chunked, re-extracted from PDF) —
        otherwise stale chunks from a previous run stay mixed in."""
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass  # didn't exist yet, nothing to delete
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[dict], embeddings, write_batch: int = 500):
        """
        chunks: list of chunk records as produced by chunker.chunk_case()
        embeddings: array-like, same length/order as chunks
        """
        ids = [c["chunk_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "case_index": c["case_index"],
                "case_number": c["case_number"],
                "volume": c["volume"],
                "legal_category": c["legal_category"],
                "page_range": c["page_range"],
                "chunk_index": c["chunk_index"],
                "num_chunks": c["num_chunks"],
            }
            for c in chunks
        ]

        for i in range(0, len(ids), write_batch):
            self.collection.add(
                ids=ids[i:i + write_batch],
                embeddings=embeddings[i:i + write_batch].tolist()
                if hasattr(embeddings, "tolist") else embeddings[i:i + write_batch],
                documents=documents[i:i + write_batch],
                metadatas=metadatas[i:i + write_batch],
            )

    def query(self, query_embedding, top_k: int = 5, where: dict | None = None):
        """
        Returns Chroma's raw query result dict: {ids, documents, metadatas,
        distances}, each a list-of-lists (one inner list per query — we
        always pass a single query here, so index [0]).
        """
        return self.collection.query(
            query_embeddings=[query_embedding.tolist()
                              if hasattr(query_embedding, "tolist") else query_embedding],
            n_results=top_k,
            where=where,
        )

    def count(self) -> int:
        return self.collection.count()
