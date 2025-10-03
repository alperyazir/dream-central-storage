"""Integration-style tests for application build uploads."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.services import RelocationError, RelocationReport


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


def test_delete_app_requires_authentication() -> None:
    client = TestClient(app)
    response = client.request("DELETE", "/apps/macos", json={"path": "macos/1.0/"})
    assert response.status_code in {401, 403}


def test_delete_app_validates_platform(monkeypatch) -> None:
    from app.routers import apps as apps_router

    monkeypatch.setattr(apps_router, "move_prefix_to_trash", lambda **kwargs: RelocationReport("apps", "trash", "macos/1.0/", "apps/macos/1.0/", 0))

    client = TestClient(app)
    response = client.request(
        "DELETE",
        "/apps/linux",
        json={"path": "linux/1.0/"},
        headers=_auth_headers(),
    )
    assert response.status_code == 400


def test_delete_app_validates_path_prefix(monkeypatch) -> None:
    from app.routers import apps as apps_router

    monkeypatch.setattr(apps_router, "move_prefix_to_trash", lambda **kwargs: RelocationReport("apps", "trash", "macos/1.0/", "apps/macos/1.0/", 0))

    client = TestClient(app)
    response = client.request(
        "DELETE",
        "/apps/macos",
        json={"path": "windows/1.0/"},
        headers=_auth_headers(),
    )
    assert response.status_code == 400


def test_delete_app_validates_missing_version(monkeypatch) -> None:
    from app.routers import apps as apps_router

    monkeypatch.setattr(apps_router, "move_prefix_to_trash", lambda **kwargs: RelocationReport("apps", "trash", "macos/1.0/", "apps/macos/1.0/", 0))

    client = TestClient(app)
    response = client.request(
        "DELETE",
        "/apps/macos",
        json={"path": "macos"},
        headers=_auth_headers(),
    )
    assert response.status_code == 400


def test_delete_app_success(monkeypatch) -> None:
    from app.routers import apps as apps_router

    captured = {}

    def fake_move_prefix_to_trash(**kwargs):
        captured["prefix"] = kwargs["prefix"]
        return RelocationReport(
            source_bucket="apps",
            destination_bucket="trash",
            source_prefix="macos/1.0/",
            destination_prefix="apps/macos/1.0/",
            objects_moved=3,
        )

    monkeypatch.setattr(apps_router, "move_prefix_to_trash", fake_move_prefix_to_trash)

    client = TestClient(app)
    response = client.request(
        "DELETE",
        "/apps/macos",
        json={"path": "macos/1.0/"},
        headers=_auth_headers(),
    )
    assert response.status_code == 204
    assert captured["prefix"] == "macos/1.0/"


def test_delete_app_handles_relocation_error(monkeypatch) -> None:
    from app.routers import apps as apps_router

    monkeypatch.setattr(
        apps_router,
        "move_prefix_to_trash",
        MagicMock(side_effect=RelocationError("failed")),
    )

    client = TestClient(app)
    response = client.request(
        "DELETE",
        "/apps/macos",
        json={"path": "macos/1.0/"},
        headers=_auth_headers(),
    )
    assert response.status_code == 502
