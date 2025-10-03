"""High-level storage helpers for uploading content to MinIO."""

from __future__ import annotations

import io
import logging
import zipfile
from dataclasses import dataclass
from typing import Iterable

from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error


class UploadError(Exception):
    """Raised when an upload archive cannot be processed."""


class RelocationError(Exception):
    """Raised when stored objects cannot be moved between buckets."""


class RestorationError(Exception):
    """Raised when objects cannot be restored from the trash bucket."""


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RelocationReport:
    """Summary of a MinIO relocation operation."""

    source_bucket: str
    destination_bucket: str
    source_prefix: str
    destination_prefix: str
    objects_moved: int


@dataclass(slots=True)
class TrashEntry:
    """Aggregated metadata for a prefix stored in the trash bucket."""

    key: str
    bucket: str
    path: str
    item_type: str
    object_count: int
    total_size: int
    metadata: dict[str, str] | None = None


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


def list_trash_entries(client: Minio, trash_bucket: str) -> list[TrashEntry]:
    """Aggregate trash bucket contents into logical restore targets."""

    aggregates: dict[str, TrashEntry] = {}

    try:
        objects = client.list_objects(trash_bucket, recursive=True)
    except S3Error as exc:  # pragma: no cover - propagated to caller
        logger.error("Failed listing trash bucket '%s': %s", trash_bucket, exc)
        raise RelocationError(f"Unable to list trash bucket '{trash_bucket}'") from exc

    for obj in objects:
        object_name = obj.object_name
        if not object_name or object_name.endswith("/"):
            continue

        parts = [segment for segment in object_name.split("/") if segment]
        if not parts:
            continue

        bucket = parts[0]
        item_type = "unknown"
        prefix_parts: list[str]
        metadata: dict[str, str] | None = None

        if bucket == "books" and len(parts) >= 3:
            item_type = "book"
            prefix_parts = parts[1:3]
            metadata = {"publisher": parts[1], "book_name": parts[2]}
        elif bucket == "apps" and len(parts) >= 3:
            item_type = "app"
            prefix_parts = parts[1:3]
            metadata = {"platform": parts[1], "version": parts[2]}
        else:
            # Fallback: treat the next segment as the identifier when available.
            prefix_parts = parts[1:2] if len(parts) >= 2 else []

        if not prefix_parts:
            continue

        key_prefix = "/".join([bucket, *prefix_parts])
        aggregate = aggregates.get(key_prefix)
        if aggregate is None:
            aggregates[key_prefix] = TrashEntry(
                key=f"{key_prefix}/",
                bucket=bucket,
                path="/".join(prefix_parts),
                item_type=item_type,
                object_count=0,
                total_size=0,
                metadata=metadata,
            )
            aggregate = aggregates[key_prefix]
        else:
            # Preserve metadata from the first encountered object.
            if aggregate.metadata is None and metadata:
                aggregate.metadata = metadata

        aggregate.object_count += 1
        aggregate.total_size += obj.size or 0

    return sorted(aggregates.values(), key=lambda entry: entry.key)


def move_prefix_to_trash(
    *,
    client: Minio,
    source_bucket: str,
    prefix: str,
    trash_bucket: str,
) -> RelocationReport:
    """Move all objects under ``prefix`` into the trash bucket while preserving paths."""

    normalized_prefix = prefix if prefix.endswith("/") else f"{prefix}/"
    destination_prefix = f"{source_bucket}/{normalized_prefix}"

    try:
        objects = list(client.list_objects(source_bucket, prefix=normalized_prefix, recursive=True))
    except S3Error as exc:  # pragma: no cover - network/MinIO failure
        logger.error("Failed listing objects for prefix '%s/%s': %s", source_bucket, normalized_prefix, exc)
        raise RelocationError(f"Unable to list objects for prefix '{normalized_prefix}'") from exc

    moved = 0
    for obj in objects:
        source_object = obj.object_name
        relative_path = source_object[len(normalized_prefix) :]
        destination_object = f"{destination_prefix}{relative_path}"

        try:
            client.copy_object(
                trash_bucket,
                destination_object,
                CopySource(source_bucket, source_object),
            )
            client.remove_object(source_bucket, source_object)
        except S3Error as exc:  # pragma: no cover - depends on MinIO responses
            logger.error(
                "Failed relocating object '%s/%s' to '%s/%s': %s",
                source_bucket,
                source_object,
                trash_bucket,
                destination_object,
                exc,
            )
            raise RelocationError(f"Unable to relocate object '{source_object}'") from exc
        moved += 1

    report = RelocationReport(
        source_bucket=source_bucket,
        destination_bucket=trash_bucket,
        source_prefix=normalized_prefix,
        destination_prefix=destination_prefix,
        objects_moved=moved,
    )

    logger.info(
        "Relocated %s objects from %s/%s to %s/%s",
        moved,
        report.source_bucket,
        report.source_prefix,
        report.destination_bucket,
        report.destination_prefix,
    )
    return report


def restore_prefix_from_trash(
    *,
    client: Minio,
    trash_bucket: str,
    key: str,
) -> RelocationReport:
    """Restore a previously soft-deleted prefix from the trash bucket."""

    normalized_key = key if key.endswith("/") else f"{key}/"
    parts = [segment for segment in normalized_key.split("/") if segment]
    if len(parts) < 2:
        raise RestorationError("Invalid trash key; expected bucket/prefix pairs")

    destination_bucket = parts[0]
    destination_prefix = "/".join(parts[1:])
    if destination_prefix and not destination_prefix.endswith("/"):
        destination_prefix = f"{destination_prefix}/"

    try:
        objects = list(
            client.list_objects(trash_bucket, prefix=normalized_key, recursive=True)
        )
    except S3Error as exc:  # pragma: no cover - depends on MinIO responses
        logger.error("Failed listing trash objects for '%s': %s", normalized_key, exc)
        raise RestorationError(f"Unable to list trash entry '{normalized_key}'") from exc

    if not objects:
        raise RestorationError(f"No trash objects found for key '{normalized_key}'")

    restored = 0
    for obj in objects:
        source_object = obj.object_name
        relative_path = source_object[len(normalized_key) :]
        if relative_path == "":  # Defensive guard for prefix placeholders
            continue

        destination_object = f"{destination_prefix}{relative_path}"

        try:
            client.copy_object(
                destination_bucket,
                destination_object,
                CopySource(trash_bucket, source_object),
            )
            client.remove_object(trash_bucket, source_object)
        except S3Error as exc:  # pragma: no cover - depends on MinIO responses
            logger.error(
                "Failed restoring object '%s' to '%s/%s': %s",
                source_object,
                destination_bucket,
                destination_object,
                exc,
            )
            raise RestorationError(f"Unable to restore object '{source_object}'") from exc
        restored += 1

    report = RelocationReport(
        source_bucket=trash_bucket,
        destination_bucket=destination_bucket,
        source_prefix=normalized_key,
        destination_prefix=destination_prefix,
        objects_moved=restored,
    )

    logger.info(
        "Restored %s objects from %s/%s to %s/%s",
        restored,
        report.source_bucket,
        report.source_prefix,
        report.destination_bucket,
        report.destination_prefix,
    )

    return report
