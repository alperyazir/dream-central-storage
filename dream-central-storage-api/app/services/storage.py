from __future__ import annotations

import logging
from typing import Any

from app.core.config import S3Config

logger = logging.getLogger(__name__)


def _import_minio():
    try:
        from minio import Minio  # type: ignore

        return Minio
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.error("MinIO client not available: %s", exc)
        return None


def create_minio_client(cfg: S3Config) -> Any | None:
    """Create a MinIO client from configuration.

    Returns None if config is incomplete or library is missing.
    """
    if not (cfg.endpoint and cfg.access_key and cfg.secret_key):
        logger.warning("S3 config incomplete; skipping client creation")
        return None

    Minio = _import_minio()
    if Minio is None:
        return None

    # Strip scheme if present; Minio accepts host:port when secure specified
    endpoint = cfg.endpoint
    if endpoint.startswith("http://"):
        endpoint = endpoint[len("http://") :]
    elif endpoint.startswith("https://"):
        endpoint = endpoint[len("https://") :]

    client = Minio(
        endpoint,
        access_key=cfg.access_key,
        secret_key=cfg.secret_key,
        secure=cfg.secure,
    )
    return client


def check_s3_connection(cfg: S3Config) -> tuple[bool, str]:
    """Verify we can reach S3 and the bucket exists.

    Returns (ok, message)
    """
    client = create_minio_client(cfg)
    if client is None:
        return False, "S3 client unavailable or config incomplete"

    try:
        # If bucket not present, this still verifies connectivity; we only report status
        bucket = cfg.bucket
        if not bucket:
            # Listing buckets to verify connectivity
            list(client.list_buckets())  # type: ignore[attr-defined]
            return True, "Connected to S3 (bucket not set)"

        exists = client.bucket_exists(bucket)  # type: ignore[attr-defined]
        if exists:
            return True, f"Connected; bucket '{bucket}' exists"
        return False, f"Connected; bucket '{bucket}' missing"
    except Exception as exc:  # pragma: no cover - depends on env
        logger.exception("S3 connectivity check failed: %s", exc)
        return False, f"Error: {exc}"
