from fastapi import APIRouter

from app.core.config import get_settings


router = APIRouter()


@router.get("/", tags=["Health"])
def read_health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
