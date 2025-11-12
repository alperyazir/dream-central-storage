"""Integration-style tests for storage listing endpoints."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db import get_db
from app.main import app
from app.services.storage import DeletionReport


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

    fake_book_repo = MagicMock()
    fake_book_repo.get_by_publisher_and_name.return_value = None
    monkeypatch.setattr(storage, "_book_repository", fake_book_repo)

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


def test_delete_trash_entry_removes_objects_and_metadata(monkeypatch) -> None:
    from app.routers import storage

    old_timestamp = datetime.now(UTC) - timedelta(days=10)
    fake_client = MagicMock()
    fake_client.list_objects.return_value = [
        SimpleNamespace(object_name="books/Press/Atlas/file.txt", last_modified=old_timestamp)
    ]
    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    fake_book = MagicMock()
    fake_repo = MagicMock()
    fake_repo.get_by_publisher_and_name.return_value = fake_book
    monkeypatch.setattr(storage, "_book_repository", fake_repo)

    client = TestClient(app)
    response = client.request(
        "DELETE",
        "/storage/trash",
        headers=_auth_headers(),
        json={"key": "books/Press/Atlas/"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deleted_key"] == "books/Press/Atlas/"
    assert body["objects_removed"] == 1
    fake_client.remove_object.assert_called_once_with("trash", "books/Press/Atlas/file.txt")
    fake_repo.delete.assert_called_once_with(ANY, fake_book)


def test_delete_trash_entry_blocks_within_retention(monkeypatch) -> None:
    from app.routers import storage

    recent_timestamp = datetime.now(UTC) - timedelta(days=2)
    fake_client = MagicMock()
    fake_client.list_objects.return_value = [
        SimpleNamespace(object_name="apps/macos/2.0/build.zip", last_modified=recent_timestamp)
    ]
    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.request(
        "DELETE",
        "/storage/trash",
        headers=_auth_headers(),
        json={"key": "apps/macos/2.0/"},
    )

    assert response.status_code == 409
    assert "retention" in response.json()["detail"].lower()
    fake_client.remove_object.assert_not_called()


def test_delete_trash_entry_force_requires_reason(monkeypatch) -> None:
    from app.routers import storage

    fake_client = MagicMock()
    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.request(
        "DELETE",
        "/storage/trash",
        headers=_auth_headers(),
        json={"key": "apps/linux/1.4.6/", "force": True},
    )

    assert response.status_code == 422
    assert "override_reason" in response.json()["detail"].lower()
    fake_client.list_objects.assert_not_called()


def test_delete_trash_entry_force_with_reason(monkeypatch) -> None:
    from app.routers import storage

    deletion_report = DeletionReport(
        trash_bucket="trash",
        key="apps/linux/1.4.6/",
        objects_removed=2,
    )

    def fake_delete_prefix_from_trash(**kwargs):
        assert kwargs["force"] is True
        assert kwargs["override_reason"] == "Compliance approved"
        return deletion_report

    monkeypatch.setattr(storage, "delete_prefix_from_trash", fake_delete_prefix_from_trash)

    client = TestClient(app)
    response = client.request(
        "DELETE",
        "/storage/trash",
        headers=_auth_headers(),
        json={
            "key": "apps/linux/1.4.6/",
            "force": True,
            "override_reason": "  Compliance approved  ",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deleted_key"] == "apps/linux/1.4.6/"
    assert body["objects_removed"] == 2


def test_delete_trash_entry_returns_not_found(monkeypatch) -> None:
    from app.routers import storage

    fake_client = MagicMock()
    fake_client.list_objects.return_value = []
    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.request(
        "DELETE",
        "/storage/trash",
        headers=_auth_headers(),
        json={"key": "books/Press/Missing/"},
    )

    assert response.status_code == 404


def test_get_book_config_returns_payload(monkeypatch) -> None:
    from app.routers import storage

    payload = {"publisher": "Dream", "book_name": "Sky", "language": "English"}
    raw = json.dumps(payload).encode("utf-8")

    fake_obj = MagicMock()
    fake_obj.read.return_value = raw
    fake_obj.close = MagicMock()
    fake_obj.release_conn = MagicMock()

    fake_client = MagicMock()
    fake_client.stat_object.return_value = SimpleNamespace(size=len(raw), content_type="application/json")
    fake_client.get_object.return_value = fake_obj

    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.get(
        "/storage/books/Dream/Sky/config",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.json() == payload
    fake_obj.close.assert_called_once()
    fake_obj.release_conn.assert_called_once()


def test_download_book_object_streams_content(monkeypatch) -> None:
    from app.routers import storage

    data = b"chapter contents"
    fake_obj = MagicMock()
    fake_obj.stream.return_value = iter([data])
    fake_obj.close = MagicMock()
    fake_obj.release_conn = MagicMock()

    fake_client = MagicMock()
    fake_client.stat_object.return_value = SimpleNamespace(size=len(data), content_type="text/plain")
    fake_client.get_object.return_value = fake_obj

    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.get(
        "/storage/books/Dream/Sky/object",
        params={"path": "chapter1.txt"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.content == data
    assert response.headers["content-disposition"].startswith("attachment;")
    fake_obj.close.assert_called_once()
    fake_obj.release_conn.assert_called_once()
