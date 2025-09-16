from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.v1.deps import get_current_user
from app.core.config import load_s3_config
from app.services.storage import create_minio_client

router = APIRouter(prefix="/api/v1/apps", tags=["apps"])


Platform = Literal["linux", "macos", "windows"]


@router.post("/", status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_user)])
async def upload_app_build(
    version: Annotated[str, Form()],
    platform: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> dict[str, str]:
    version = (version or "").strip()
    if not version:
        raise HTTPException(status_code=422, detail="version is required")

    norm_platform = (platform or "").strip().lower()
    if norm_platform not in {"linux", "macos", "windows"}:
        raise HTTPException(
            status_code=422, detail="platform must be one of: linux, macos, windows"
        )

    # Streamed upload: avoid loading entire file into memory
    # Reset pointer in case the framework pre-read any bytes
    await file.seek(0)

    cfg = load_s3_config()
    if not cfg.bucket:
        raise HTTPException(status_code=500, detail="S3 bucket not configured")

    client = create_minio_client(cfg)
    if client is None:
        raise HTTPException(status_code=500, detail="S3 client unavailable")

    object_name = f"apps/{norm_platform}/{version}/flowbook.zip"

    try:
        # Stream directly from the underlying file-like object. Use multipart with unknown length.
        client.put_object(  # type: ignore[attr-defined]
            cfg.bucket,
            object_name,
            data=file.file,  # SpooledTemporaryFile / file-like object
            length=-1,  # unknown size → multipart upload
            part_size=10 * 1024 * 1024,  # 10MB parts
            content_type=file.content_type or "application/zip",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"upload failed: {exc}") from exc

    location = f"s3://{cfg.bucket}/{object_name}"
    return {"version": version, "platform": norm_platform, "location": location}
