"""
backend/app/api/v1/router.py
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import chat, health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])