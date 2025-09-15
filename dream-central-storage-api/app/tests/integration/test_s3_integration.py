import os
import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import load_s3_config
from app.main import app
from app.services.storage import check_s3_connection, create_minio_client


@pytest.mark.integration
def test_storage_health_with_minio():
    # Arrange env for local MinIO; allow override via env if user has custom values
    os.environ.setdefault("S3_ENDPOINT", "http://localhost:9000")
    os.environ.setdefault("S3_ACCESS_KEY", "minioadmin")
    os.environ.setdefault("S3_SECRET_KEY", "minioadmin")
    os.environ.setdefault("S3_BUCKET", "dream-assets-int")
    os.environ.setdefault("S3_SECURE", "false")

    cfg = load_s3_config()

    # Skip if MinIO SDK unavailable or config incomplete
    client = create_minio_client(cfg)
    if client is None:
        pytest.skip("MinIO client unavailable or env not set; skipping integration test")

    # Wait briefly for MinIO to come up if running via docker-compose
    deadline = time.time() + 30
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            list(client.list_buckets())
            last_err = None
            break
        except Exception as exc:  # pragma: no cover - timing dependent
            last_err = exc
            time.sleep(1)

    if last_err is not None:
        pytest.skip(f"MinIO not reachable: {last_err}")

    # Ensure bucket exists for test
    if not client.bucket_exists(cfg.bucket):  # type: ignore[arg-type]
        client.make_bucket(cfg.bucket)  # type: ignore[arg-type]

    # Sanity check direct connectivity helper
    ok, msg = check_s3_connection(cfg)
    assert ok, f"Direct S3 check failed: {msg}"

    # Exercise API endpoint
    with TestClient(app) as http:
        resp = http.get("/storage/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("status") == "ok"
        assert "bucket" in body.get("detail", "").lower() or "connected" in body.get("detail", "").lower()

