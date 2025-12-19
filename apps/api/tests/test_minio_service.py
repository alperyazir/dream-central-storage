"""Unit tests for MinIO service helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from minio.error import S3Error

from app.core.config import Settings
from app.services.minio import ensure_buckets, get_minio_client


def test_get_minio_client_uses_settings() -> None:
    settings = Settings(
        minio_endpoint="play.min.io",
        minio_access_key="access",
        minio_secret_key="secret",
        minio_secure=True,
    )

    with patch("app.services.minio.Minio") as minio_cls:
        get_minio_client(settings)
        minio_cls.assert_called_once_with(
            "play.min.io",
            access_key="access",
            secret_key="secret",
            secure=True,
        )


def test_ensure_buckets_creates_missing_bucket() -> None:
    client = MagicMock()
    client.bucket_exists.side_effect = [False, True]

    ensure_buckets(client, ["publishers", "apps"])

    client.bucket_exists.assert_any_call("publishers")
    client.bucket_exists.assert_any_call("apps")
    client.make_bucket.assert_called_once_with("publishers")


def test_ensure_buckets_skips_existing_bucket() -> None:
    client = MagicMock()
    client.bucket_exists.return_value = True

    ensure_buckets(client, ["publishers"])

    client.make_bucket.assert_not_called()


def test_ensure_buckets_raises_runtime_error_on_s3_failure() -> None:
    client = MagicMock()
    error = S3Error(
        "BucketAlreadyOwnedByYou",
        "message",
        "resource",
        "request_id",
        "host_id",
        MagicMock(),
        "bucket",
    )
    client.bucket_exists.side_effect = error

    with pytest.raises(RuntimeError, match="Unable to ensure bucket 'publishers'"):
        ensure_buckets(client, ["publishers"])
