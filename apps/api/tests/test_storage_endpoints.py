"""Integration-style tests for storage listing endpoints."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db import get_db
from app.main import app


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch):
    from app.routers import storage

    monkeypatch.setattr(storage, "_require_admin", lambda credentials, db: 1)

    fake_client = MagicMock()
    fake_client.list_objects.return_value = [
        SimpleNamespace(object_name="Dream/Sky/chapter1.txt", size=10),
        SimpleNamespace(object_name="Dream/Sky/notes/readme.md", size=5),
    ]
    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    def fake_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = fake_get_db

    yield

    app.dependency_overrides.pop(get_db, None)


def _auth_headers() -> dict[str, str]:
    token = create_access_token(subject="1")
    return {"Authorization": f"Bearer {token}"}


def test_list_book_contents() -> None:
    client = TestClient(app)
    response = client.get(
        "/storage/books/Dream/Sky",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == "Dream/Sky/"
    assert len(body["children"]) == 2


def test_list_app_contents() -> None:
    from app.routers import storage

    fake_client = MagicMock()
    fake_client.list_objects.return_value = [
        SimpleNamespace(object_name="macos/1.0/app.exe", size=100)
    ]
    storage.get_minio_client = lambda settings: fake_client

    client = TestClient(app)
    response = client.get(
        "/storage/apps/macos",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == "macos/"
    assert body["children"][0]["path"].endswith("1.0/")


def test_list_app_contents_linux() -> None:
    from app.routers import storage

    fake_client = MagicMock()
    fake_client.list_objects.return_value = [
        SimpleNamespace(object_name="linux/2.0/app.tar.gz", size=150)
    ]
    storage.get_minio_client = lambda settings: fake_client

    client = TestClient(app)
    response = client.get(
        "/storage/apps/linux",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == "linux/"
    assert body["children"][0]["path"].endswith("2.0/")


def test_list_app_contents_with_version() -> None:
    from app.routers import storage

    fake_client = MagicMock()
    fake_client.list_objects.return_value = [
        SimpleNamespace(object_name="macos/1.1/app.exe", size=200)
    ]
    storage.get_minio_client = lambda settings: fake_client

    client = TestClient(app)
    response = client.get(
        "/storage/apps/macos",
        params={"version": "1.1"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == "macos/1.1/"
    assert body["children"][0]["path"].endswith("app.exe")
