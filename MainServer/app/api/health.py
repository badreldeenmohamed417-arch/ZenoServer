from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.core.database import engine
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/")
async def home():
    return {"status": "running", "service": "zeno-api"}


@router.get("/health/live")
async def live():
    return {"status": "ok"}


@router.get("/health/ready")
async def ready():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        # Redis remains available for workers but is not a request-path dependency in V1.
        return {
            "status": "ready",
            "database": "ok",
            "redis": {
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "required": False,
            },
        }
    except Exception as exc:
        raise HTTPException(503, "Database is unavailable") from exc
