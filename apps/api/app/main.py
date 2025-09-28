from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import apps, auth, books, health, storage
from app.services import ensure_buckets, get_minio_client


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = get_minio_client(settings)
    ensure_buckets(client, settings.minio_buckets)
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.resolved_cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(books.router)
app.include_router(apps.router)
app.include_router(storage.router)
app.include_router(health.router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Explicit health endpoint for readiness probes."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }
