"""Upload endpoints for application builds."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.services import UploadError, get_minio_client, upload_app_archive

router = APIRouter(prefix="/apps", tags=["Apps"])
_bearer_scheme = HTTPBearer(auto_error=True)

ALLOWED_PLATFORMS = {"macos", "windows"}


def _require_admin(credentials: HTTPAuthorizationCredentials) -> int:
    token = credentials.credentials
    try:
        payload = decode_access_token(token, settings=get_settings())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        return int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


@router.post("/{platform}/upload", status_code=status.HTTP_201_CREATED)
async def upload_application_build(
    platform: str,
    file: UploadFile,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
):
    """Upload an application build archive to the apps bucket."""

    _require_admin(credentials)

    normalized_platform = platform.lower()
    if normalized_platform not in ALLOWED_PLATFORMS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported platform")

    settings = get_settings()
    client = get_minio_client(settings)
    version = uuid.uuid4().hex

    archive_bytes = await file.read()
    try:
        manifest = upload_app_archive(
            client=client,
            archive_bytes=archive_bytes,
            bucket=settings.minio_apps_bucket,
            platform=normalized_platform,
            version=version,
            content_type="application/octet-stream",
        )
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to upload application build",
        ) from exc

    return {
        "platform": normalized_platform,
        "version": version,
        "files": manifest,
    }
