"""MinIO client helpers and bootstrap utilities."""

from __future__ import annotations

import logging
from typing import Iterable

from minio import Minio
from minio.error import S3Error

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def get_minio_client(settings: Settings | None = None) -> Minio:
    """Create a MinIO client using application settings."""

    config = settings or get_settings()
    return Minio(
        config.minio_endpoint,
        access_key=config.minio_access_key,
        secret_key=config.minio_secret_key,
        secure=config.minio_secure,
    )


def ensure_buckets(client: Minio, bucket_names: Iterable[str]) -> None:
    """Ensure that each bucket in ``bucket_names`` exists."""

    for bucket in bucket_names:
        try:
            if client.bucket_exists(bucket):
                logger.debug("MinIO bucket '%s' already exists", bucket)
                continue
            client.make_bucket(bucket)
            logger.info("Created MinIO bucket '%s'", bucket)
        except S3Error as exc:  # pragma: no cover - specific to MinIO SDK
            logger.error("Failed to ensure bucket '%s': %s", bucket, exc)
            raise RuntimeError(f"Unable to ensure bucket '{bucket}'") from exc
        except Exception as exc:  # pragma: no cover - guard unexpected errors
            logger.error("Unexpected error ensuring bucket '%s': %s", bucket, exc)
            raise
