"""Service layer utilities for external integrations."""

from .minio import ensure_buckets, get_minio_client
from .storage import UploadError, upload_book_archive

__all__ = [
    "get_minio_client",
    "ensure_buckets",
    "upload_book_archive",
    "UploadError",
]
