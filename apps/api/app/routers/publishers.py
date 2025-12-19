"""CRUD endpoints for publisher metadata."""

from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token, verify_api_key_from_db
from app.db import get_db
from app.repositories.publisher import PublisherRepository
from app.repositories.user import UserRepository
from app.schemas.asset import AssetFileInfo, AssetTypeInfo, PublisherAssetsResponse
from app.schemas.book import BookRead
from app.schemas.publisher import PublisherCreate, PublisherRead, PublisherUpdate
from app.services import get_minio_client, move_prefix_to_trash, RelocationError

router = APIRouter(prefix="/publishers", tags=["Publishers"])
_bearer_scheme = HTTPBearer(auto_error=True)
_publisher_repository = PublisherRepository()
_user_repository = UserRepository()
logger = logging.getLogger(__name__)

# Asset type validation
ASSET_TYPE_PATTERN = re.compile(r"^[a-z0-9_-]{1,50}$")
RESERVED_ASSET_TYPES = {"books", "trash", "temp"}


def validate_asset_type(asset_type: str) -> None:
    """Validate asset type format and check for reserved names."""
    if not ASSET_TYPE_PATTERN.match(asset_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid asset type format. Must be lowercase alphanumeric, hyphens, or underscores (1-50 chars)",
        )
    if asset_type in RESERVED_ASSET_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{asset_type}' is a reserved name",
        )


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
        return -1

    # Both JWT and API key failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )


@router.post("/", response_model=PublisherRead, status_code=status.HTTP_201_CREATED)
def create_publisher(
    payload: PublisherCreate,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> PublisherRead:
    """Create a new publisher record."""

    _require_admin(credentials, db)

    try:
        publisher = _publisher_repository.create(db, data=payload.model_dump())
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Publisher with name '{payload.name}' already exists",
        )

    return PublisherRead.model_validate(publisher)


@router.get("/", response_model=list[PublisherRead])
def list_publishers(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> list[PublisherRead]:
    """Return all publishers with pagination."""

    _require_admin(credentials, db)
    publishers = _publisher_repository.list_paginated(db, skip=skip, limit=limit)
    return [PublisherRead.model_validate(p) for p in publishers]


@router.get("/{publisher_id}", response_model=PublisherRead)
def get_publisher(
    publisher_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> PublisherRead:
    """Retrieve a single publisher by ID."""

    _require_admin(credentials, db)
    publisher = _publisher_repository.get(db, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )
    return PublisherRead.model_validate(publisher)


@router.get("/by-name/{name}", response_model=PublisherRead)
def get_publisher_by_name(
    name: str,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> PublisherRead:
    """Retrieve a single publisher by unique name."""

    _require_admin(credentials, db)
    publisher = _publisher_repository.get_by_name(db, name)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )
    return PublisherRead.model_validate(publisher)


@router.put("/{publisher_id}", response_model=PublisherRead)
def update_publisher(
    publisher_id: int,
    payload: PublisherUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> PublisherRead:
    """Update metadata for an existing publisher."""

    _require_admin(credentials, db)
    publisher = _publisher_repository.get(db, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return PublisherRead.model_validate(publisher)

    try:
        updated = _publisher_repository.update(db, publisher, data=update_data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Publisher with name '{payload.name}' already exists",
        )

    return PublisherRead.model_validate(updated)


@router.delete("/{publisher_id}", response_model=PublisherRead)
def soft_delete_publisher(
    publisher_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> PublisherRead:
    """Soft-delete a publisher by setting status to inactive."""

    _require_admin(credentials, db)
    publisher = _publisher_repository.get(db, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    # Soft-delete: set status to inactive
    updated = _publisher_repository.update(db, publisher, data={"status": "inactive"})
    return PublisherRead.model_validate(updated)


@router.get("/{publisher_id}/books", response_model=list[BookRead])
def get_publisher_books(
    publisher_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> list[BookRead]:
    """List all books for a specific publisher."""

    _require_admin(credentials, db)
    publisher = _publisher_repository.get_with_books(db, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    return [BookRead.model_validate(book) for book in publisher.books]


@router.get("/{publisher_id}/assets", response_model=PublisherAssetsResponse)
def list_publisher_assets(
    publisher_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> PublisherAssetsResponse:
    """List all asset types for a publisher with file counts and sizes."""

    _require_admin(credentials, db)
    publisher = _publisher_repository.get(db, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    settings = get_settings()
    client = get_minio_client(settings)
    assets_prefix = f"{publisher.name}/assets/"

    # List all folders under assets/
    asset_types: dict[str, AssetTypeInfo] = {}
    try:
        objects = client.list_objects(
            settings.minio_publishers_bucket,
            prefix=assets_prefix,
            recursive=True,
        )
        for obj in objects:
            # Extract asset type from path: {publisher}/assets/{type}/{filename}
            rel_path = obj.object_name[len(assets_prefix) :]
            if "/" in rel_path:
                asset_type = rel_path.split("/")[0]
                if asset_type not in asset_types:
                    asset_types[asset_type] = AssetTypeInfo(
                        name=asset_type,
                        file_count=0,
                        total_size=0,
                    )
                asset_types[asset_type].file_count += 1
                asset_types[asset_type].total_size += obj.size
    except Exception as e:
        logger.error(f"Error listing assets for publisher {publisher_id}: {e}")
        # Return empty list if no assets or error
        pass

    return PublisherAssetsResponse(
        publisher_id=publisher.id,
        publisher_name=publisher.name,
        asset_types=list(asset_types.values()),
    )


@router.get("/{publisher_id}/assets/{asset_type}", response_model=list[AssetFileInfo])
def list_asset_type_files(
    publisher_id: int,
    asset_type: str,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> list[AssetFileInfo]:
    """List all files in a specific asset type for a publisher."""

    _require_admin(credentials, db)
    validate_asset_type(asset_type)

    publisher = _publisher_repository.get(db, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    settings = get_settings()
    client = get_minio_client(settings)
    prefix = f"{publisher.name}/assets/{asset_type}/"

    files: list[AssetFileInfo] = []
    try:
        objects = client.list_objects(
            settings.minio_publishers_bucket,
            prefix=prefix,
            recursive=True,
        )
        for obj in objects:
            # Extract filename from full path
            filename = obj.object_name[len(prefix) :]
            files.append(
                AssetFileInfo(
                    name=filename,
                    path=obj.object_name,
                    size=obj.size,
                    content_type=obj.content_type or "application/octet-stream",
                    last_modified=obj.last_modified,
                )
            )
    except Exception as e:
        logger.error(f"Error listing files for asset type {asset_type}: {e}")
        # Return empty list if no files or error
        pass

    return files


@router.post("/{publisher_id}/assets/{asset_type}", response_model=AssetFileInfo, status_code=status.HTTP_201_CREATED)
async def upload_asset_file(
    publisher_id: int,
    asset_type: str,
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> AssetFileInfo:
    """Upload a file to a specific asset type for a publisher."""

    _require_admin(credentials, db)
    validate_asset_type(asset_type)

    publisher = _publisher_repository.get(db, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    settings = get_settings()
    client = get_minio_client(settings)
    object_key = f"{publisher.name}/assets/{asset_type}/{file.filename}"

    # Read file contents
    contents = await file.read()
    file_size = len(contents)

    # Upload to MinIO
    try:
        client.put_object(
            settings.minio_publishers_bucket,
            object_key,
            io.BytesIO(contents),
            length=file_size,
            content_type=file.content_type or "application/octet-stream",
        )
    except Exception as e:
        logger.error(f"Error uploading asset file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file",
        )

    return AssetFileInfo(
        name=file.filename,
        path=object_key,
        size=file_size,
        content_type=file.content_type or "application/octet-stream",
        last_modified=datetime.now(timezone.utc),
    )


@router.get("/{publisher_id}/assets/{asset_type}/{filename}")
def download_asset_file(
    publisher_id: int,
    asset_type: str,
    filename: str,
    db: Session = Depends(get_db),
):
    """Download an asset file."""
    from fastapi.responses import StreamingResponse

    validate_asset_type(asset_type)

    publisher = _publisher_repository.get(db, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    settings = get_settings()
    client = get_minio_client(settings)
    object_key = f"{publisher.name}/assets/{asset_type}/{filename}"

    try:
        response = client.get_object(settings.minio_publishers_bucket, object_key)
        stat = client.stat_object(settings.minio_publishers_bucket, object_key)

        return StreamingResponse(
            response,
            media_type=stat.content_type or "application/octet-stream",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
                "Content-Length": str(stat.size),
            },
        )
    except Exception as e:
        logger.error(f"Error downloading asset file: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )


@router.delete("/{publisher_id}/assets/{asset_type}/{filename}")
def delete_asset_file(
    publisher_id: int,
    asset_type: str,
    filename: str,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """Soft-delete an asset file by moving it to trash."""

    _require_admin(credentials, db)
    validate_asset_type(asset_type)

    publisher = _publisher_repository.get(db, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    settings = get_settings()
    client = get_minio_client(settings)
    object_key = f"{publisher.name}/assets/{asset_type}/{filename}"

    # Move to trash
    try:
        report = move_prefix_to_trash(
            client=client,
            source_bucket=settings.minio_publishers_bucket,
            prefix=object_key,
            trash_bucket=settings.minio_trash_bucket,
        )
    except RelocationError as e:
        logger.error(f"Error deleting asset file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {e}",
        )

    return {
        "message": "File moved to trash",
        "objects_moved": report.objects_moved,
        "trash_key": report.destination_prefix,
    }
