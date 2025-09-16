import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.endpoints.private import router as private_router
from app.core.config import load_auth_config, load_s3_config
from app.middleware.auth import AuthMiddleware
from app.services.storage import check_s3_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.getLogger("uvicorn").info("Dream Central Storage API started")
    # Story 1.2: verify S3 connectivity on startup
    cfg = load_s3_config()
    ok, msg = check_s3_connection(cfg)
    if ok:
        logging.getLogger("uvicorn").info("S3 check: %s", msg)
    else:
        logging.getLogger("uvicorn.error").warning("S3 check failed: %s", msg)
    yield


app = FastAPI(title="Dream Central Storage API", lifespan=lifespan)

# Story 1.3: register auth middleware with public bypasses
_auth_cfg = load_auth_config()
app.add_middleware(
    AuthMiddleware,
    token=_auth_cfg.bearer_token,
    public_paths=("/health", "/storage/health"),
)

# Routers
app.include_router(private_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/storage/health")
def storage_health() -> dict[str, str]:
    """Report S3 storage connectivity and bucket status."""
    cfg = load_s3_config()
    ok, msg = check_s3_connection(cfg)
    return {"status": "ok" if ok else "error", "detail": msg}


# Using lifespan above instead of deprecated on_event startup
