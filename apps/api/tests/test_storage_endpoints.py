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
    assert response.headers["content-disposition"].startswith("inline;")
    assert response.headers["accept-ranges"] == "bytes"
    fake_obj.close.assert_called_once()
    fake_obj.release_conn.assert_called_once()


# ============================================================================
# HTTP Range Request Tests (Streaming Support)
# ============================================================================


def test_download_book_object_range_request_partial_content(monkeypatch) -> None:
    """Test that Range header returns 206 Partial Content with correct headers."""
    from app.routers import storage

    # Full file is 100 bytes, requesting bytes 0-9 (first 10 bytes)
    full_data = b"x" * 100
    partial_data = full_data[0:10]

    fake_obj = MagicMock()
    fake_obj.stream.return_value = iter([partial_data])
    fake_obj.close = MagicMock()
    fake_obj.release_conn = MagicMock()

    fake_client = MagicMock()
    fake_client.stat_object.return_value = SimpleNamespace(size=100, content_type="audio/mpeg")
    fake_client.get_object.return_value = fake_obj

    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    headers = _auth_headers()
    headers["Range"] = "bytes=0-9"

    response = client.get(
        "/storage/books/Dream/Sky/object",
        params={"path": "audio/test.mp3"},
        headers=headers,
    )

    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 0-9/100"
    assert response.headers["content-length"] == "10"
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-type"] == "audio/mpeg"

    # Verify MinIO was called with offset and length
    fake_client.get_object.assert_called_once()
    call_kwargs = fake_client.get_object.call_args
    assert call_kwargs.kwargs.get("offset") == 0
    assert call_kwargs.kwargs.get("length") == 10


def test_download_book_object_range_request_open_end(monkeypatch) -> None:
    """Test Range header with open end (bytes=50-)."""
    from app.routers import storage

    full_size = 100
    partial_data = b"x" * 50  # bytes 50-99

    fake_obj = MagicMock()
    fake_obj.stream.return_value = iter([partial_data])
    fake_obj.close = MagicMock()
    fake_obj.release_conn = MagicMock()

    fake_client = MagicMock()
    fake_client.stat_object.return_value = SimpleNamespace(size=full_size, content_type="video/mp4")
    fake_client.get_object.return_value = fake_obj

    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    headers = _auth_headers()
    headers["Range"] = "bytes=50-"

    response = client.get(
        "/storage/books/Dream/Sky/object",
        params={"path": "videos/intro.mp4"},
        headers=headers,
    )

    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 50-99/100"
    assert response.headers["content-length"] == "50"

    # Verify MinIO was called with offset=50, length=50
    call_kwargs = fake_client.get_object.call_args
    assert call_kwargs.kwargs.get("offset") == 50
    assert call_kwargs.kwargs.get("length") == 50


def test_download_book_object_range_request_suffix(monkeypatch) -> None:
    """Test Range header with suffix (bytes=-20 means last 20 bytes)."""
    from app.routers import storage

    full_size = 100
    partial_data = b"x" * 20  # bytes 80-99

    fake_obj = MagicMock()
    fake_obj.stream.return_value = iter([partial_data])
    fake_obj.close = MagicMock()
    fake_obj.release_conn = MagicMock()

    fake_client = MagicMock()
    fake_client.stat_object.return_value = SimpleNamespace(size=full_size, content_type="audio/mpeg")
    fake_client.get_object.return_value = fake_obj

    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    headers = _auth_headers()
    headers["Range"] = "bytes=-20"

    response = client.get(
        "/storage/books/Dream/Sky/object",
        params={"path": "audio/test.mp3"},
        headers=headers,
    )

    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 80-99/100"
    assert response.headers["content-length"] == "20"

    # Verify MinIO was called with offset=80, length=20
    call_kwargs = fake_client.get_object.call_args
    assert call_kwargs.kwargs.get("offset") == 80
    assert call_kwargs.kwargs.get("length") == 20


def test_download_book_object_range_invalid_format(monkeypatch) -> None:
    """Test that invalid Range header format returns 416."""
    from app.routers import storage

    fake_client = MagicMock()
    fake_client.stat_object.return_value = SimpleNamespace(size=100, content_type="audio/mpeg")

    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    headers = _auth_headers()
    headers["Range"] = "invalid-range-format"

    response = client.get(
        "/storage/books/Dream/Sky/object",
        params={"path": "audio/test.mp3"},
        headers=headers,
    )

    assert response.status_code == 416
    assert "content-range" in response.headers
    assert response.headers["content-range"] == "bytes */100"


def test_download_book_object_range_out_of_bounds(monkeypatch) -> None:
    """Test that out-of-bounds Range returns 416."""
    from app.routers import storage

    fake_client = MagicMock()
    fake_client.stat_object.return_value = SimpleNamespace(size=100, content_type="audio/mpeg")

    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    headers = _auth_headers()
    headers["Range"] = "bytes=150-200"  # Beyond file size

    response = client.get(
        "/storage/books/Dream/Sky/object",
        params={"path": "audio/test.mp3"},
        headers=headers,
    )

    assert response.status_code == 416


def test_download_book_object_mime_type_detection(monkeypatch) -> None:
    """Test that MIME types are correctly detected from file extension."""
    from app.routers import storage

    test_cases = [
        ("audio/track.mp3", "audio/mpeg"),
        ("videos/intro.mp4", "video/mp4"),
        ("audio/sound.wav", "audio/wav"),
        ("videos/clip.webm", "video/webm"),
        ("subtitles/en.srt", "text/plain"),
    ]

    for path, expected_mime in test_cases:
        data = b"test content"
        fake_obj = MagicMock()
        fake_obj.stream.return_value = iter([data])
        fake_obj.close = MagicMock()
        fake_obj.release_conn = MagicMock()

        fake_client = MagicMock()
        # MinIO returns generic type, but we should override based on extension
        fake_client.stat_object.return_value = SimpleNamespace(
            size=len(data), content_type="application/octet-stream"
        )
        fake_client.get_object.return_value = fake_obj

        monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

        client = TestClient(app)
        response = client.get(
            "/storage/books/Dream/Sky/object",
            params={"path": path},
            headers=_auth_headers(),
        )

        assert response.status_code == 200
        # Content-Type may include charset for text types
        assert response.headers["content-type"].startswith(expected_mime), f"Failed for {path}"


def test_download_book_object_no_range_includes_accept_ranges(monkeypatch) -> None:
    """Test that responses without Range header still include Accept-Ranges header."""
    from app.routers import storage

    data = b"full file content"
    fake_obj = MagicMock()
    fake_obj.stream.return_value = iter([data])
    fake_obj.close = MagicMock()
    fake_obj.release_conn = MagicMock()

    fake_client = MagicMock()
    fake_client.stat_object.return_value = SimpleNamespace(size=len(data), content_type="audio/mpeg")
    fake_client.get_object.return_value = fake_obj

    monkeypatch.setattr(storage, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.get(
        "/storage/books/Dream/Sky/object",
        params={"path": "audio/test.mp3"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    # This tells browsers that Range requests are supported
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-length"] == str(len(data))
