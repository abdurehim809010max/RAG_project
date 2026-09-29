"""
backend/app/api/v1/router.py
"""

"""
backend/app/api/v1/router.py
"""

from fastapi import APIRouter

# Only import the endpoints that you (Person 1) currently have
from backend.app.api.v1.endpoints import chat, health

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# TODO: Uncomment these when Person 3 (Ingestion) and Person 4 (Auth) merge their work
# from backend.app.api.v1.endpoints import auth, documents
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# api_router.include_router(documents.router, prefix="/documents", tags=["documents"])