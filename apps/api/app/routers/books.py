"""CRUD endpoints for book metadata."""

from __future__ import annotations

import io
import json
import logging
import zipfile
from collections.abc import Iterable

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from sqlalchemy.orm import Session, object_session

from app.core.config import get_settings
from app.core.security import decode_access_token, verify_api_key_from_db
from app.db import get_db
from app.repositories.book import BookRepository
from app.repositories.user import UserRepository
from app.schemas.book import BookCreate, BookRead, BookUpdate
from app.services import (
    RelocationError,
    UploadConflictError,
    UploadError,
    ensure_version_target,
    extract_manifest_version,
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
    """Validate JWT token or API key and ensure authentication is valid."""

    token = credentials.credentials

    # Try JWT first
    try:
        payload = decode_access_token(token, settings=get_settings())
        subject = payload.get("sub")
        if subject is not None:
            try:
                user_id = int(subject)
                user = _user_repository.get(db, user_id)
                if user is not None:
                    return user_id
            except (TypeError, ValueError):
                pass
    except ValueError:
        pass  # JWT failed, try API key

    # Try API key
    api_key_info = verify_api_key_from_db(token, db)
    if api_key_info is not None:
        # API key authentication successful
        # Return a special value to indicate API key auth (or could return the api_key_id)
        # For now, return -1 to indicate API key authentication (not a user_id)
        return -1

    # Both JWT and API key failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )


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
    override: bool = Query(
        False,
        description="When true, replace an existing version folder if present instead of raising a conflict.",
    ),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
):
    """Upload a zipped book folder to MinIO for the specified book."""
    _require_admin(credentials, db)
    book = _book_repository.get_by_id(db, book_id)
    if book is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    contents = await file.read()
    try:
        version = extract_manifest_version(contents)
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    settings = get_settings()
    client = get_minio_client(settings)

    prefix = f"{book.publisher}/{book.book_name}/{version}/"

    try:
        existing_prefix = ensure_version_target(
            client=client,
            bucket=settings.minio_books_bucket,
            prefix=prefix,
            version=version,
            override=override,
        )
    except UploadConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "code": "VERSION_EXISTS",
                "version": exc.version,
            },
        ) from exc
    except UploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to verify existing book assets",
        ) from exc

    if existing_prefix and override:
        try:
            move_prefix_to_trash(
                client=client,
                source_bucket=settings.minio_books_bucket,
                prefix=prefix,
                trash_bucket=settings.minio_trash_bucket,
            )
        except RelocationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to relocate existing version before override",
            ) from exc

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

    if book.version != version:
        session_obj = object_session(book)
        if session_obj is not None:
            _book_repository.update(db, book, data={"version": version})
        else:
            book.version = version

    logger.info(
        "Uploaded book assets for book_id=%s version %s (override=%s, files=%s)",
        book_id,
        version,
        bool(existing_prefix and override),
        len(manifest),
    )

    return {"book_id": book_id, "version": version, "files": manifest}


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_new_book(
    file: UploadFile,
    override: bool = Query(
        False,
        description="When true, replace an existing version folder if present instead of raising a conflict.",
    ),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
):
    """Upload a zipped book folder and create new metadata from the archive."""

    admin_id = _require_admin(credentials, db)

    contents = await file.read()

    try:
        version = extract_manifest_version(contents)
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        create_payload = _extract_book_metadata(contents)
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    existing = _book_repository.get_by_publisher_and_name(
        db,
        publisher=create_payload.publisher,
        book_name=create_payload.book_name,
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Book already exists; please use update mode to upload new content.",
        )

    if create_payload.version and create_payload.version.strip() and create_payload.version.strip() != version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="config.json version must match data/version",
        )

    book_data = create_payload.model_dump()
    for field in ("publisher", "book_name", "language", "category", "version"):
        value = book_data.get(field)
        if isinstance(value, str):
            book_data[field] = value.strip()
    book_data["version"] = version
    # Default new uploads to published status so they appear immediately in listings.
    if book_data.get("status") is None or book_data["status"] == BookStatusEnum.DRAFT:
        book_data["status"] = BookStatusEnum.PUBLISHED

    settings = get_settings()
    client = get_minio_client(settings)
    object_prefix = f"{book_data['publisher']}/{book_data['book_name']}/{version}/"

    try:
        existing_prefix = ensure_version_target(
            client=client,
            bucket=settings.minio_books_bucket,
            prefix=object_prefix,
            version=version,
            override=override,
        )
    except UploadConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "code": "VERSION_EXISTS",
                "version": exc.version,
            },
        ) from exc
    except UploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to verify existing book assets",
        ) from exc

    if existing_prefix and override:
        try:
            move_prefix_to_trash(
                client=client,
                source_bucket=settings.minio_books_bucket,
                prefix=object_prefix,
                trash_bucket=settings.minio_trash_bucket,
            )
        except RelocationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to relocate existing version before override",
            ) from exc

    try:
        manifest = upload_book_archive(
            client=client,
            archive_bytes=contents,
            bucket=settings.minio_books_bucket,
            object_prefix=object_prefix,
            content_type="application/octet-stream",
        )
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload book archive",
        ) from exc

    book = _book_repository.create(db, data=book_data)
    book_read = BookRead.model_validate(book)

    logger.info(
        "User %s uploaded new book %s version %s under prefix %s with %s files",
        admin_id,
        book_read.id,
        version,
        object_prefix,
        len(manifest),
    )

    return {"book": book_read.model_dump(), "version": version, "files": manifest}


_CONFIG_ALIASES: dict[str, tuple[str, ...]] = {
    "publisher": ("publisher", "publisher_name", "publisherName"),
    "book_name": ("book_name", "book_title", "bookTitle", "title"),
    "language": ("language", "lang"),
    "category": ("category", "subject", "book_category", "bookCategory"),
    "version": ("version", "book_version", "bookVersion"),
    "status": ("status", "book_status", "bookStatus"),
}


def _extract_book_metadata(archive_bytes: bytes) -> BookCreate:
    """Return book metadata parsed from ``config.json`` with legacy fallbacks."""

    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
            config_path = _first_matching(names, "config.json")
            metadata_path = _first_matching(names, "metadata.json")

            if config_path is None:
                raise UploadError("config.json is missing from the archive")

            config_payload = _read_json_from_archive(
                archive, config_path, label="config.json", required=True
            )
            metadata_payload = None
            if metadata_path is not None:
                try:
                    metadata_payload = _read_json_from_archive(
                        archive,
                        metadata_path,
                        label="metadata.json",
                        required=False,
                    )
                except UploadError:
                    metadata_payload = None

    except zipfile.BadZipFile as exc:
        raise UploadError("Uploaded file is not a valid ZIP archive") from exc

    try:
        payload, used_metadata = _coalesce_metadata(config_payload, metadata_payload)
        if metadata_payload is not None:
            logger.warning(
                "metadata.json detected in upload archive; this file is deprecated%s",
                " and was used to fill missing fields" if used_metadata else "",
            )
        return BookCreate.model_validate(payload)
    except ValidationError as exc:
        missing = {
            error["loc"][-1] for error in exc.errors() if error.get("type") == "missing"
        }
        if missing:
            missing_fields = ", ".join(sorted(str(field) for field in missing))
            message = f"config.json is missing required fields: {missing_fields}"
        else:
            message = "config.json contains invalid values"
        raise UploadError(message) from exc


def _first_matching(names: Iterable[str], suffix: str) -> str | None:
    suffix_lower = suffix.lower()
    return next((name for name in names if name.lower().endswith(suffix_lower)), None)


def _read_json_from_archive(
    archive: zipfile.ZipFile,
    path: str,
    *,
    label: str,
    required: bool,
) -> dict[str, object]:
    try:
        with archive.open(path) as file_handle:
            try:
                raw_text = file_handle.read().decode("utf-8")
            except UnicodeDecodeError as exc:
                message = f"{label} must be UTF-8 encoded"
                if required:
                    raise UploadError(message) from exc
                raise UploadError(message) from exc
    except KeyError as exc:
        if required:
            raise UploadError(f"{label} could not be opened") from exc
        raise UploadError(f"{label} could not be opened") from exc

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        message = f"{label} is not valid JSON"
        if required:
            raise UploadError(message) from exc
        raise UploadError(message) from exc

    if not isinstance(payload, dict):
        message = f"{label} must contain a JSON object"
        if required:
            raise UploadError(message)
        raise UploadError(message)

    return payload


def _coalesce_metadata(
    config_payload: dict[str, object],
    metadata_payload: dict[str, object] | None,
) -> tuple[dict[str, object], bool]:
    result: dict[str, object] = {}
    metadata_used = False

    for target, aliases in _CONFIG_ALIASES.items():
        value = _first_non_empty(config_payload, aliases)
        if value is None and metadata_payload is not None:
            value = _first_non_empty(metadata_payload, aliases)
            if value is not None:
                metadata_used = True

        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                result[target] = normalized
            elif target in {"version", "status"}:
                # Preserve empty optional values as omitted.
                continue
        elif value is not None:
            result[target] = value

    return result, metadata_used


def _first_non_empty(payload: dict[str, object], aliases: Iterable[str]) -> object | None:
    for alias in aliases:
        if alias in payload:
            candidate = payload[alias]
            if isinstance(candidate, str):
                stripped = candidate.strip()
                if stripped:
                    return stripped
            elif candidate is not None:
                return candidate
    return None
