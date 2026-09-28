"""
backend/app/services/rag/embeddings.py

Local embedding client. Wraps sentence-transformers so callers never have
to remember model-specific quirks (like e5's required "query: " /
"passage: " prefixes) — get it right here once, not at every call site.

If you swap to an API-based embedding provider later (OpenAI, Cohere),
this is the only file that should need to change — pipeline.py and
vector_store.py both depend on this interface, not on sentence-transformers
directly.
"""

from sentence_transformers import SentenceTransformer

DEFAULT_MODEL = "intfloat/multilingual-e5-base"


class EmbeddingClient:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        try:
            # Load directly from local cache to avoid Hugging Face network
            # checks, DNS timeouts (Errno 11001), and HF_TOKEN warnings.
            self._model = SentenceTransformer(model_name, local_files_only=True)
        except OSError:
            # Model is not cached on disk yet (first run on a new machine);
            # download it from Hugging Face Hub.
            self._model = SentenceTransformer(model_name, local_files_only=False)

    def embed_passages(self, texts: list[str], batch_size: int = 32):
        """Embed document chunks for indexing. e5 models expect the
        'passage: ' prefix on indexed text — this is part of how the
        model was trained, not optional decoration."""
        prefixed = [f"passage: {t}" for t in texts]
        return self._model.encode(
            prefixed,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
        )

    def embed_queries(self, texts: list[str], batch_size: int = 32):
        """Embed user questions for retrieval. Must use 'query: ' here,
        not 'passage: ' — mixing these up silently degrades retrieval
        quality without raising any error, so it's worth getting right."""
        prefixed = [f"query: {t}" for t in texts]
        return self._model.encode(
            prefixed,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

    def embed_query(self, text: str):
        """Convenience wrapper for a single query string."""
        return self.embed_queries([text])[0]