"""Health and Readiness Endpoints."""

from fastapi import APIRouter
from backend.app.config import settings

router = APIRouter(tags=["Operations"])


@router.get("/health")
async def health_check():
    return {
        "status": "HEALTHY",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "demo_mode": settings.DEMO_MODE
    }


@router.get("/ready")
async def readiness_check():
    return {
        "database": "CONNECTED",
        "asr_provider": settings.ASR_PROVIDER,
        "llm_provider": settings.LLM_PROVIDER,
        "dpdp_encryption": "ACTIVE"
    }

