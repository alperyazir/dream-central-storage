from __future__ import annotations

import io
import os
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_s3_config
from app.main import app
from app.services.storage import create_minio_client


@pytest.mark.integration
def test_apps_upload_to_minio():
    # Arrange env for local MinIO; allow override via env if user has custom values
    os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
    os.environ.setdefault("S3_ACCESS_KEY", "minioadmin")
    os.environ.setdefault("S3_SECRET_KEY", "minioadmin")
    os.environ.setdefault("S3_BUCKET", "dream-assets-int")
    os.environ.setdefault("S3_SECURE", "false")
    os.environ.setdefault("AUTH_BEARER_TOKEN", "secret-token")

    cfg = load_s3_config()
    client = create_minio_client(cfg)
    if client is None:
        pytest.skip("MinIO client unavailable or env not set; skipping integration test")

    # Wait briefly for MinIO
    deadline = time.time() + 30
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            list(client.list_buckets())
            last_err = None
            break
        except Exception as exc:  # pragma: no cover
            last_err = exc
            time.sleep(1)

    if last_err is not None:
        pytest.skip(f"MinIO not reachable: {last_err}")

    # Ensure bucket exists for test
    if not client.bucket_exists(cfg.bucket):  # type: ignore[arg-type]
        client.make_bucket(cfg.bucket)  # type: ignore[arg-type]

    object_path = "apps/linux/1.0.0/flowbook.zip"

    # Exercise API endpoint
    with TestClient(app) as http:
        files = {"file": ("flowbook.zip", io.BytesIO(b"data"), "application/zip")}
        data = {"version": "1.0.0", "platform": "linux"}
        resp = http.post(
            "/api/v1/apps/",
            files=files,
            data=data,
            headers={"Authorization": "Bearer secret-token"},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body.get("platform") == "linux"
        assert body.get("version") == "1.0.0"
        assert body.get("location", "").endswith(object_path)

    # Verify object exists
    stat = client.stat_object(cfg.bucket, object_path)  # type: ignore[arg-type]
    assert stat is not None
