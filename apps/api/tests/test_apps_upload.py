"""Integration-style tests for application build uploads."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app


def _make_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("app.exe", "binarydata")
    return buffer.getvalue()


def _auth_headers() -> dict[str, str]:
    token = create_access_token(subject="1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def patch_upload(monkeypatch):
    from app.routers import apps

    def fake_upload(**kwargs):
        return [{"path": f"{kwargs['platform']}/{kwargs['version']}/app.exe", "size": len("binarydata")}]

    monkeypatch.setattr(apps, "upload_app_archive", fake_upload)
    monkeypatch.setattr(apps, "get_minio_client", lambda settings: MagicMock())

    yield


def test_upload_app_success():
    client = TestClient(app)
    response = client.post(
        "/apps/macos/upload",
        files={"file": ("build.zip", _make_zip_bytes(), "application/zip")},
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["platform"] == "macos"
    assert len(body["files"]) == 1


def test_upload_app_requires_authentication():
    client = TestClient(app)
    response = client.post(
        "/apps/macos/upload",
        files={"file": ("build.zip", _make_zip_bytes(), "application/zip")},
    )
    assert response.status_code in {401, 403}


def test_upload_app_rejects_unknown_platform():
    client = TestClient(app)
    response = client.post(
        "/apps/android/upload",
        files={"file": ("build.zip", _make_zip_bytes(), "application/zip")},
        headers=_auth_headers(),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported platform"


def test_upload_app_handles_upload_error(monkeypatch):
    from app.routers import apps

    monkeypatch.setattr(apps, "upload_app_archive", MagicMock(side_effect=apps.UploadError("bad archive")))

    client = TestClient(app)
    response = client.post(
        "/apps/macos/upload",
        files={"file": ("build.zip", b"bad", "application/zip")},
        headers=_auth_headers(),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "bad archive"
