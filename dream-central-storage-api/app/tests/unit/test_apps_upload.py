from __future__ import annotations

import importlib
import io

import pytest
from fastapi.testclient import TestClient


def _reload_app():
    import app.main as main_mod

    importlib.reload(main_mod)
    return main_mod.app


class _FakeMinio:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int, str]] = []

    def put_object(self, bucket: str, object_name: str, data, length: int, content_type: str | None = None):  # type: ignore[no-untyped-def]
        # drain data to simulate upload
        if hasattr(data, "read"):
            _ = data.read()
        self.calls.append((bucket, object_name, length, content_type or ""))


def test_upload_app_build_happy_path(monkeypatch: pytest.MonkeyPatch):
    # Env
    monkeypatch.setenv("AUTH_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("S3_BUCKET", "dream-assets")

    # Patch client factory at usage site
    import app.api.v1.endpoints.assets as assets_mod

    importlib.reload(assets_mod)
    fake = _FakeMinio()
    monkeypatch.setattr(assets_mod, "create_minio_client", lambda cfg: fake)

    app = _reload_app()
    client = TestClient(app)

    files = {"file": ("flowbook.zip", io.BytesIO(b"data"), "application/zip")}
    data = {"version": "1.0.0", "platform": "linux"}
    resp = client.post(
        "/api/v1/apps/",
        files=files,
        data=data,
        headers={"Authorization": "Bearer secret-token"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["version"] == "1.0.0"
    assert body["platform"] == "linux"
    assert body["location"].endswith("apps/linux/1.0.0/flowbook.zip")
    # Verify client called
    assert fake.calls and fake.calls[0][1].endswith("apps/linux/1.0.0/flowbook.zip")


def test_upload_requires_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_BEARER_TOKEN", "secret-token")
    app = _reload_app()
    client = TestClient(app)
    resp = client.post("/api/v1/apps/")
    assert resp.status_code == 401


def test_upload_validates_inputs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_BEARER_TOKEN", "secret-token")
    monkeypatch.setenv("S3_BUCKET", "dream-assets")
    app = _reload_app()
    client = TestClient(app)

    # Missing version
    files = {"file": ("flowbook.zip", io.BytesIO(b"data"), "application/zip")}
    resp = client.post(
        "/api/v1/apps/",
        files=files,
        data={"platform": "linux"},
        headers={"Authorization": "Bearer secret-token"},
    )
    assert resp.status_code == 422

    # Missing/invalid platform
    resp2 = client.post(
        "/api/v1/apps/",
        files=files,
        data={"version": "1.0.0", "platform": "bad"},
        headers={"Authorization": "Bearer secret-token"},
    )
    assert resp2.status_code == 422
