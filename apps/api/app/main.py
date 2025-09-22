from fastapi import FastAPI

from app.core.config import get_settings
from app.routers import auth, health


settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.include_router(auth.router)
app.include_router(health.router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Explicit health endpoint for readiness probes."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
