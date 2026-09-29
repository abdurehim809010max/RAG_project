"""
backend/app/core/config.py

Single source of truth for app settings. Everything that was previously a
hardcoded default or a command-line flag default scattered across scripts
(model names, Chroma path, collection name, chunk size, top_k) lives here,
so the API layer reads them from one place.

Values come from, in priority order:
  1. real environment variables
  2. backend/.env
  3. the defaults below

Paths are resolved relative to the backend/ folder (not the current working
directory), so the app finds its data no matter where uvicorn is launched
from.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[2] is backend/
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        extra="ignore",  # .env may hold keys this app doesn't declare
    )

    # --- LLM (generation) ---
    gemini_api_key: str
    gemini_model: str = "gemini-3.8-flash"

    # --- Embeddings ---
    embedding_model: str = "intfloat/multilingual-e5-base"

    # --- Vector store ---
    vector_db_dir: str = str(BACKEND_DIR / "data" / "vector_db")
    collection_name: str = "volume_15"

    # --- Chunking (used by ingestion) ---
    chunk_size: int = 800
    chunk_overlap: int = 150

    # --- Retrieval ---
    top_k: int = 5

    # --- Authentication ---
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is read once, not on every request."""
    return Settings()
