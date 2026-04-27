from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.db.mongo import ping_database

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@router.get("/health/db")
def health_db() -> dict[str, str]:
    try:
        return ping_database()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

