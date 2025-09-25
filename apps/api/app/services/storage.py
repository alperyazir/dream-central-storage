"""High-level storage helpers for uploading content to MinIO."""

from __future__ import annotations

import io
import zipfile
from collections import defaultdict
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


def list_objects_tree(client: Minio, bucket: str, prefix: str) -> dict[str, object]:
    """Return a hierarchical tree of objects under ``prefix`` within ``bucket``."""

    root = {
        "path": prefix,
        "type": "folder",
        "children": {},
    }

    objects = client.list_objects(bucket, prefix=prefix, recursive=True)
    for obj in objects:
        rel_path = obj.object_name[len(prefix) :]
        parts = [p for p in rel_path.split("/") if p]
        current = root

        for part in parts[:-1]:
            children = current.setdefault("children", {})
            if part not in children:
                children[part] = {
                    "path": f"{current['path']}{part}/",
                    "type": "folder",
                    "children": {},
                }
            current = children[part]

        if not parts:
            continue

        file_name = parts[-1]
        children = current.setdefault("children", {})
        children[file_name] = {
            "path": f"{current['path']}{file_name}",
            "type": "file",
            "size": obj.size,
        }

    return _normalize_tree(root)


def _normalize_tree(node: dict[str, object]) -> dict[str, object]:
    children = node.get("children")
    if not children:
        node["children"] = []
        return node

    normalized_children = []
    for name, child in children.items():
        normalized_children.append(_normalize_tree(child))
    node["children"] = sorted(normalized_children, key=lambda item: item["path"])
    return node
