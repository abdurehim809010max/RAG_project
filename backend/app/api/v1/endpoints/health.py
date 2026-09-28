"""
backend/app/api/v1/endpoints/health.py
"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("")
def health_check(request: Request):
    pipeline = getattr(request.app.state, "rag_pipeline", None)
    return {
        "status": "ok",
        "ready": pipeline is not None,
    }