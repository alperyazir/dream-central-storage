"""Integration-style tests for the book upload endpoint."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.models.book import Book, BookStatusEnum


def _make_zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("chapter1.txt", "Once upon a time")
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
