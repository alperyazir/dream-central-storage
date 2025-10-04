"""Integration-style tests for the book upload endpoint."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.models.book import Book, BookStatusEnum


def _make_zip_bytes(
    *,
    config: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("chapter1.txt", "Once upon a time")
        if config is not None:
            archive.writestr("config.json", json.dumps(config))
        if metadata is not None:
            archive.writestr("metadata.json", json.dumps(metadata))
    return buffer.getvalue()


def _auth_headers() -> dict[str, str]:
    token = create_access_token(subject="1")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def setup_repositories(monkeypatch):
    from app.routers import books

    monkeypatch.setattr(books, "_require_admin", lambda credentials, db: 1)

    book = Book(
        id=1,
        publisher="Dream",
        book_name="Sky",
        language="en",
        category="fiction",
        status=BookStatusEnum.DRAFT,
    )
    book.created_at = book.updated_at = None

    monkeypatch.setattr(books._book_repository, "get_by_id", lambda db, identifier: book if identifier == 1 else None)

    yield


def test_upload_book_success(monkeypatch):
    from app.routers import books

    def fake_upload(**kwargs):
        return [{"path": "Dream/Sky/chapter1.txt", "size": len("Once upon a time")}]

    monkeypatch.setattr(books, "upload_book_archive", fake_upload)
    monkeypatch.setattr(books, "get_minio_client", lambda settings: MagicMock())

    client = TestClient(app)
    response = client.post(
        "/books/1/upload",
        files={"file": ("book.zip", _make_zip_bytes(), "application/zip")},
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["book_id"] == 1
    assert body["files"][0]["path"] == "Dream/Sky/chapter1.txt"


def test_upload_book_requires_authentication():
    client = TestClient(app)
    response = client.post(
        "/books/1/upload",
        files={"file": ("book.zip", _make_zip_bytes(), "application/zip")},
    )
    assert response.status_code in {401, 403}


def test_upload_book_returns_404_for_missing_book(monkeypatch):
    from app.routers import books

    monkeypatch.setattr(books._book_repository, "get_by_id", lambda db, identifier: None)

    client = TestClient(app)
    response = client.post(
        "/books/999/upload",
        files={"file": ("book.zip", _make_zip_bytes(), "application/zip")},
        headers=_auth_headers(),
    )
    assert response.status_code == 404


def test_upload_book_handles_upload_error(monkeypatch):
    from app.routers import books

    monkeypatch.setattr(books, "upload_book_archive", MagicMock(side_effect=books.UploadError("bad archive")))
    monkeypatch.setattr(books, "get_minio_client", lambda settings: MagicMock())

    client = TestClient(app)
    response = client.post(
        "/books/1/upload",
        files={"file": ("book.zip", _make_zip_bytes(), "application/zip")},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "bad archive"


def test_upload_new_book_creates_metadata(monkeypatch):
    from app.routers import books

    captured = {}

    def fake_upload(**kwargs):
        captured["prefix"] = kwargs["object_prefix"]
        return [{"path": f"{kwargs['object_prefix']}chapter1.txt", "size": 16}]

    created_book = Book(
        id=2,
        publisher="Dream Press",
        book_name="Sky Atlas",
        language="en",
        category="fiction",
        status=BookStatusEnum.PUBLISHED,
    )
    created_book.created_at = created_book.updated_at = datetime.now(timezone.utc)

    monkeypatch.setattr(books, "upload_book_archive", fake_upload)
    monkeypatch.setattr(books, "get_minio_client", lambda settings: MagicMock())
    monkeypatch.setattr(
        books._book_repository,
        "get_by_publisher_and_name",
        lambda db, publisher, book_name: None,
    )

    captured_create: dict[str, object] = {}

    def fake_create(db, data):
        captured_create.update(data)
        return created_book

    monkeypatch.setattr(books._book_repository, "create", fake_create)

    client = TestClient(app)
    config = {
        "publisher_name": "Dream Press",
        "book_title": " Sky Atlas ",
        "language": "en",
        "category": "fiction",
        "status": "draft",
    }

    response = client.post(
        "/books/upload",
        files={"file": ("book.zip", _make_zip_bytes(config=config), "application/zip")},
        headers=_auth_headers(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["book"]["id"] == 2
    assert body["book"]["book_name"] == "Sky Atlas"
    assert captured["prefix"] == "Dream Press/Sky Atlas/"
    # Status defaults to published even if metadata requested draft.
    assert captured_create["status"] == BookStatusEnum.PUBLISHED


def test_upload_new_book_requires_config(monkeypatch):
    from app.routers import books

    monkeypatch.setattr(books, "upload_book_archive", MagicMock())
    monkeypatch.setattr(books, "get_minio_client", lambda settings: MagicMock())
    monkeypatch.setattr(
        books._book_repository,
        "get_by_publisher_and_name",
        lambda db, publisher, book_name: None,
    )

    client = TestClient(app)
    response = client.post(
        "/books/upload",
        files={"file": ("book.zip", _make_zip_bytes(), "application/zip")},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    assert "config.json" in response.json()["detail"].lower()


def test_upload_new_book_rejects_invalid_config(monkeypatch):
    from app.routers import books

    monkeypatch.setattr(books, "upload_book_archive", MagicMock())
    monkeypatch.setattr(books, "get_minio_client", lambda settings: MagicMock())
    monkeypatch.setattr(
        books._book_repository,
        "get_by_publisher_and_name",
        lambda db, publisher, book_name: None,
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("config.json", "{not: 'json'}")

    client = TestClient(app)
    response = client.post(
        "/books/upload",
        files={"file": ("book.zip", buffer.getvalue(), "application/zip")},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    assert "config.json" in response.json()["detail"].lower()


def test_upload_new_book_detects_duplicates(monkeypatch):
    from app.routers import books

    existing = Book(
        id=5,
        publisher="Dream Press",
        book_name="Sky Atlas",
        language="en",
        category="fiction",
        status=BookStatusEnum.PUBLISHED,
    )
    existing.created_at = existing.updated_at = datetime.now(timezone.utc)

    monkeypatch.setattr(
        books._book_repository,
        "get_by_publisher_and_name",
        lambda db, publisher, book_name: existing,
    )

    def unexpected_upload(**kwargs):  # pragma: no cover - defensive in case of bug
        raise AssertionError("upload_book_archive should not be called for duplicate metadata")

    monkeypatch.setattr(books, "upload_book_archive", unexpected_upload)

    client = TestClient(app)
    config = {
        "publisher": "Dream Press",
        "book_name": "Sky Atlas",
        "language": "en",
        "category": "fiction",
    }

    response = client.post(
        "/books/upload",
        files={"file": ("book.zip", _make_zip_bytes(config=config), "application/zip")},
        headers=_auth_headers(),
    )

    assert response.status_code == 409
    assert "update mode" in response.json()["detail"].lower()


def test_upload_new_book_uses_metadata_as_fallback(monkeypatch, caplog):
    from app.routers import books

    monkeypatch.setattr(books, "upload_book_archive", MagicMock())
    monkeypatch.setattr(books, "get_minio_client", lambda settings: MagicMock())
    monkeypatch.setattr(
        books._book_repository,
        "get_by_publisher_and_name",
        lambda db, publisher, book_name: None,
    )
    def fake_create(db, data):
        status_value = data.get("status", BookStatusEnum.DRAFT)
        if isinstance(status_value, str):
            status_value = BookStatusEnum(status_value)
        book = Book(
            id=3,
            publisher=data["publisher"],
            book_name=data["book_name"],
            language=data["language"],
            category=data["category"],
            status=status_value,
        )
        timestamp = datetime.now(timezone.utc)
        book.created_at = book.updated_at = timestamp
        return book

    monkeypatch.setattr(books._book_repository, "create", fake_create)

    config = {
        "publisher": "Dream Press",
        "book_name": "Sky Atlas",
        "language": "en",
    }
    metadata = {
        "category": "fiction",
        "status": "draft",
    }

    client = TestClient(app)
    with caplog.at_level("WARNING"):
        response = client.post(
            "/books/upload",
            files={
                "file": (
                    "book.zip",
                    _make_zip_bytes(config=config, metadata=metadata),
                    "application/zip",
                )
            },
            headers=_auth_headers(),
        )

    assert response.status_code == 201
    warnings = " ".join(record.message for record in caplog.records if record.levelname == "WARNING")
    assert "metadata.json" in warnings
    assert "used to fill missing fields" in warnings


def test_upload_new_book_reports_missing_fields(monkeypatch):
    from app.routers import books

    monkeypatch.setattr(books, "upload_book_archive", MagicMock())
    monkeypatch.setattr(books, "get_minio_client", lambda settings: MagicMock())
    monkeypatch.setattr(
        books._book_repository,
        "get_by_publisher_and_name",
        lambda db, publisher, book_name: None,
    )

    config = {
        "publisher_name": "Dream Press",
        "book_title": "Sky Atlas",
    }

    client = TestClient(app)
    response = client.post(
        "/books/upload",
        files={"file": ("book.zip", _make_zip_bytes(config=config), "application/zip")},
        headers=_auth_headers(),
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "config.json" in detail
    assert "language" in detail
