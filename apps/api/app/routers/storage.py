"""Endpoints for listing stored content."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.services import get_minio_client, list_objects_tree

router = APIRouter(prefix="/storage", tags=["Storage"])
_bearer_scheme = HTTPBearer(auto_error=True)


def _require_admin(credentials: HTTPAuthorizationCredentials) -> None:
    token = credentials.credentials
    try:
        decode_access_token(token, settings=get_settings())
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


@router.get("/books/{publisher}/{book_name}")
async def list_book_contents(
    publisher: str,
    book_name: str,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    """List the stored files for a specific book."""

    _require_admin(credentials)
    settings = get_settings()
    client = get_minio_client(settings)
    prefix = f"{publisher}/{book_name}/"
    tree = list_objects_tree(client, settings.minio_books_bucket, prefix)
    return tree


@router.get("/apps/{platform}")
async def list_app_contents(
    platform: str,
    version: str | None = Query(default=None),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    """List stored files for application builds on a platform (optional version filter)."""

    _require_admin(credentials)
    settings = get_settings()
    client = get_minio_client(settings)

    prefix = f"{platform}/"
    if version:
        prefix = f"{prefix}{version}/"

    tree = list_objects_tree(client, settings.minio_apps_bucket, prefix)
    return tree
