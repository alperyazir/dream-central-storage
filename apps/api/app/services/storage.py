"""High-level storage helpers for uploading content to MinIO."""

from __future__ import annotations

import io
import zipfile
from typing import Iterable

from minio import Minio

from app.core.config import Settings


class UploadError(Exception):
    """Raised when an upload archive cannot be processed."""


def iter_zip_entries(archive: zipfile.ZipFile) -> Iterable[zipfile.ZipInfo]:
    """Yield only file entries from the archive, skipping directories."""

    for entry in archive.infolist():
        if entry.is_dir():
            continue
        yield entry


def upload_book_archive(
    *,
    client: Minio,
    archive_bytes: bytes,
    bucket: str,
    object_prefix: str,
    content_type: str | None = None,
) -> list[dict[str, object]]:
    """Upload the provided ZIP archive into MinIO under the given prefix.

    Returns a manifest containing uploaded file paths and sizes.
    """

    try:
        archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except zipfile.BadZipFile as exc:  # pragma: no cover - handled in tests
        raise UploadError("Uploaded file is not a valid ZIP archive") from exc

    manifest: list[dict[str, object]] = []
    for entry in iter_zip_entries(archive):
        file_path = f"{object_prefix}{entry.filename}"
        with archive.open(entry) as file_obj:
            stream = io.BytesIO(file_obj.read())
            stream.seek(0)
            client.put_object(
                bucket,
                file_path,
                stream,
                length=entry.file_size,
                content_type=content_type or "application/octet-stream",
            )
        manifest.append({"path": file_path, "size": entry.file_size})

    return manifest


def upload_app_archive(
    *,
    client: Minio,
    archive_bytes: bytes,
    bucket: str,
    platform: str,
    version: str,
    content_type: str | None = None,
) -> list[dict[str, object]]:
    """Upload an application build archive into MinIO under platform/version."""

    prefix = f"{platform}/{version}/"
    return upload_book_archive(
        client=client,
        archive_bytes=archive_bytes,
        bucket=bucket,
        object_prefix=prefix,
        content_type=content_type,
    )
