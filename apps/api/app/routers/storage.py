"""Endpoints for listing stored content and restoring items from trash."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db import get_db
from app.repositories.book import BookRepository
from app.repositories.user import UserRepository
from app.schemas.book import BookRead
from app.schemas.storage import (
    RestoreRequest,
    RestoreResponse,
    TrashDeleteRequest,
    TrashDeleteResponse,
    TrashEntryRead,
)
from app.services import (
    RestorationError,
    TrashDeletionError,
    TrashEntryNotFoundError,
    TrashRetentionError,
    delete_prefix_from_trash,
    get_minio_client,
    list_objects_tree,
    list_trash_entries,
    restore_prefix_from_trash,
)

router = APIRouter(prefix="/storage", tags=["Storage"])
_bearer_scheme = HTTPBearer(auto_error=True)
_user_repository = UserRepository()
_book_repository = BookRepository()
logger = logging.getLogger(__name__)


def _require_admin(credentials: HTTPAuthorizationCredentials, db: Session) -> int:
    token = credentials.credentials
    try:
        payload = decode_access_token(token, settings=get_settings())
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    user = _user_repository.get(db, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    return user_id


@router.get("/books/{publisher}/{book_name}")
async def list_book_contents(
    publisher: str,
    book_name: str,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
):
    """List the stored files for a specific book."""

    _require_admin(credentials, db)
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
    db: Session = Depends(get_db),
):
    """List stored files for application builds on a platform (optional version filter)."""

    _require_admin(credentials, db)
    settings = get_settings()
    client = get_minio_client(settings)

    prefix = f"{platform}/"
    if version:
        prefix = f"{prefix}{version}/"

    tree = list_objects_tree(client, settings.minio_apps_bucket, prefix)
    return tree


@router.get("/trash", response_model=list[TrashEntryRead])
async def list_trash_contents(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
):
    """Return aggregated list of items currently stored in the trash bucket."""

    _require_admin(credentials, db)
    settings = get_settings()
    client = get_minio_client(settings)
    entries = list_trash_entries(client, settings.minio_trash_bucket)
    return [
        TrashEntryRead(
            key=entry.key,
            bucket=entry.bucket,
            path=entry.path,
            item_type=entry.item_type,
            object_count=entry.object_count,
            total_size=entry.total_size,
            metadata=entry.metadata,
        )
        for entry in entries
    ]


def _parse_trash_key(key: str) -> tuple[str, list[str]]:
    normalized = key.strip()
    if not normalized:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Key is required")

    parts = [segment for segment in normalized.split("/") if segment]
    if len(parts) < 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Key is invalid")
    return parts[0], parts[1:]


def _extract_book_identifiers(path_parts: list[str]) -> tuple[str, str]:
    if len(path_parts) < 2:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Book restore key is incomplete")
    return path_parts[0], path_parts[1]


@router.post("/restore", response_model=RestoreResponse)
def restore_item(
    payload: RestoreRequest,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
):
    """Restore a soft-deleted book or application build from the trash bucket."""

    admin_id = _require_admin(credentials, db)
    bucket, path_parts = _parse_trash_key(payload.key)

    settings = get_settings()
    client = get_minio_client(settings)

    key_with_bucket = f"{bucket}/{'/'.join(path_parts)}/"

    try:
        report = restore_prefix_from_trash(
            client=client,
            trash_bucket=settings.minio_trash_bucket,
            key=key_with_bucket,
        )
    except RestorationError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "No trash objects" in message else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(status_code=status_code, detail=message) from exc

    item_type: Literal["book", "app", "unknown"] = "unknown"
    book_read: BookRead | None = None

    if bucket == "books":
        item_type = "book"
        publisher, book_name = _extract_book_identifiers(path_parts)
        book = _book_repository.get_by_publisher_and_name(
            db,
            publisher=publisher,
            book_name=book_name,
        )
        if book is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Book not found")

        try:
            restored_book = _book_repository.restore(db, book)
        except ValueError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        book_read = BookRead.model_validate(restored_book)
    elif bucket == "apps":
        item_type = "app"

    logger.info(
        "User %s restored trash key '%s'; moved %s objects",
        admin_id,
        key_with_bucket,
        report.objects_moved,
    )

    return RestoreResponse(
        restored_key=key_with_bucket,
        objects_moved=report.objects_moved,
        item_type=item_type,
        book=book_read,
    )


@router.delete("/trash", response_model=TrashDeleteResponse)
def delete_trash_entry(
    payload: TrashDeleteRequest,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
):
    """Permanently delete a trash entry after retention checks succeed."""

    admin_id = _require_admin(credentials, db)
    bucket, path_parts = _parse_trash_key(payload.key)

    settings = get_settings()
    client = get_minio_client(settings)

    key_with_bucket = f"{bucket}/{'/'.join(path_parts)}/"
    retention_period = timedelta(days=settings.trash_retention_days)

    try:
        report = delete_prefix_from_trash(
            client=client,
            trash_bucket=settings.minio_trash_bucket,
            key=key_with_bucket,
            retention=retention_period,
            force=payload.force,
        )
    except TrashEntryNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TrashRetentionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except TrashDeletionError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    item_type: Literal["book", "app", "unknown"] = "unknown"
    if bucket == "books":
        item_type = "book"
        publisher, book_name = _extract_book_identifiers(path_parts)
        book = _book_repository.get_by_publisher_and_name(
            db,
            publisher=publisher,
            book_name=book_name,
        )
        if book is not None:
            _book_repository.delete(db, book)
    elif bucket == "apps":
        item_type = "app"

    logger.info(
        "User %s permanently deleted trash key '%s'; removed %s objects (force=%s)",
        admin_id,
        key_with_bucket,
        report.objects_removed,
        payload.force,
    )

    return TrashDeleteResponse(
        deleted_key=key_with_bucket,
        objects_removed=report.objects_removed,
        item_type=item_type,
    )
