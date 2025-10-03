"""CRUD endpoints for book metadata."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db import get_db
from app.repositories.book import BookRepository
from app.repositories.user import UserRepository
from app.schemas.book import BookCreate, BookRead, BookUpdate
from app.services import (
    RelocationError,
    UploadError,
    get_minio_client,
    move_prefix_to_trash,
    upload_book_archive,
)
from app.models.book import BookStatusEnum

router = APIRouter(prefix="/books", tags=["Books"])
_bearer_scheme = HTTPBearer(auto_error=True)
_book_repository = BookRepository()
_user_repository = UserRepository()
logger = logging.getLogger(__name__)


def _require_admin(credentials: HTTPAuthorizationCredentials, db: Session) -> int:
    """Validate JWT token and ensure the referenced administrator exists."""

    token = credentials.credentials
    try:
        payload = decode_access_token(token, settings=get_settings())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = _user_repository.get(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return user_id


@router.post("/", response_model=BookRead, status_code=status.HTTP_201_CREATED)
def create_book(
    payload: BookCreate,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> BookRead:
    """Create a new book metadata record."""

    _require_admin(credentials, db)
    book = _book_repository.create(db, data=payload.model_dump())
    return BookRead.model_validate(book)


@router.get("/", response_model=list[BookRead])
def list_books(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> list[BookRead]:
    """Return all stored books."""

    _require_admin(credentials, db)
    books = _book_repository.list_all_books(db)
    return [BookRead.model_validate(book) for book in books]


@router.get("/{book_id}", response_model=BookRead)
def get_book(
    book_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> BookRead:
    """Retrieve a single book by identifier."""

    _require_admin(credentials, db)
    book = _book_repository.get_by_id(db, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return BookRead.model_validate(book)


@router.put("/{book_id}", response_model=BookRead)
def update_book(
    book_id: int,
    payload: BookUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> BookRead:
    """Update metadata for an existing book."""

    _require_admin(credentials, db)
    book = _book_repository.get_by_id(db, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return BookRead.model_validate(book)

    updated = _book_repository.update(db, book, data=update_data)
    return BookRead.model_validate(updated)


@router.delete("/{book_id}", response_model=BookRead)
def soft_delete_book(
    book_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> BookRead:
    """Soft-delete a book by archiving metadata and moving assets to the trash bucket."""

    admin_id = _require_admin(credentials, db)
    book = _book_repository.get_by_id(db, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    if book.status == BookStatusEnum.ARCHIVED:
        return BookRead.model_validate(book)

    settings = get_settings()
    client = get_minio_client(settings)
    prefix = f"{book.publisher}/{book.book_name}/"

    try:
        report = move_prefix_to_trash(
            client=client,
            source_bucket=settings.minio_books_bucket,
            prefix=prefix,
            trash_bucket=settings.minio_trash_bucket,
        )
    except RelocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to relocate book assets",
        ) from exc

    archived = _book_repository.archive(db, book)

    logger.info(
        "User %s archived book %s; moved %s objects from %s/%s to %s/%s",
        admin_id,
        archived.id,
        report.objects_moved,
        report.source_bucket,
        report.source_prefix,
        report.destination_bucket,
        report.destination_prefix,
    )

    return BookRead.model_validate(archived)


@router.post("/{book_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_book(
    book_id: int,
    file: UploadFile,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
):
    """Upload a zipped book folder to MinIO for the specified book."""

    _require_admin(credentials, db)
    book = _book_repository.get_by_id(db, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    settings = get_settings()
    client = get_minio_client(settings)
    prefix = f"{book.publisher}/{book.book_name}/"

    contents = await file.read()
    try:
        manifest = upload_book_archive(
            client=client,
            archive_bytes=contents,
            bucket=settings.minio_books_bucket,
            object_prefix=prefix,
            content_type="application/octet-stream",
        )
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload book archive",
        ) from exc

    return {"book_id": book_id, "files": manifest}
