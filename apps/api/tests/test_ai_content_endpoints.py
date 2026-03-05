"""Tests for AI content endpoints using mocks to avoid SQLite/JSONB issues."""

from __future__ import annotations

import io
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from minio.error import S3Error

from app.main import app
from app.models.book import Book, BookStatusEnum
from app.models.publisher import Publisher


@pytest.fixture
def mock_book() -> Book:
    """Create a mock book object."""
    publisher = MagicMock(spec=Publisher)
    publisher.id = 1
    publisher.name = "TestPub"

    book = MagicMock(spec=Book)
    book.id = 42
    book.publisher_id = 1
    book.book_name = "TestBook"
    book.publisher = "TestPub"
    book.publisher_rel = publisher
    book.language = "en"
    book.status = BookStatusEnum.PUBLISHED
    return book


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer mock_token"}


SAMPLE_MANIFEST = {
    "activity_type": "listening_quiz",
    "title": "Listening - Quiz (MCQ) - 5 items",
    "item_count": 5,
    "has_audio": True,
    "has_passage": False,
    "difficulty": "A2",
    "language": "en",
}

SAMPLE_CONTENT = {
    "questions": [
        {"id": "q1", "text": "What is the main idea?", "options": ["A", "B", "C"], "answer": "A"},
    ]
}

CONTENT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

def test_create_ai_content_requires_auth():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/books/42/ai-content/", json={"manifest": SAMPLE_MANIFEST, "content": SAMPLE_CONTENT})
    assert resp.status_code in {401, 403}


def test_list_ai_content_requires_auth():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/books/42/ai-content/")
    assert resp.status_code in {401, 403}


def test_get_ai_content_requires_auth():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(f"/books/42/ai-content/{CONTENT_ID}")
    assert resp.status_code in {401, 403}


def test_delete_ai_content_requires_auth():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.delete(f"/books/42/ai-content/{CONTENT_ID}")
    assert resp.status_code in {401, 403}


# ---------------------------------------------------------------------------
# 404 — book not found
# ---------------------------------------------------------------------------

@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_create_ai_content_book_not_found(mock_repo, mock_auth, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = None

    client = TestClient(app)
    resp = client.post(
        "/books/9999/ai-content/",
        json={"manifest": SAMPLE_MANIFEST, "content": SAMPLE_CONTENT},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Create AI content
# ---------------------------------------------------------------------------

@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_create_ai_content_success(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    client = TestClient(app)
    resp = client.post(
        "/books/42/ai-content/",
        json={"manifest": SAMPLE_MANIFEST, "content": SAMPLE_CONTENT},
        headers=auth_headers,
    )

    assert resp.status_code == 201
    data = resp.json()
    assert "content_id" in data
    assert "storage_path" in data
    assert mock_client.put_object.call_count == 2

    first_key = mock_client.put_object.call_args_list[0][0][1]
    second_key = mock_client.put_object.call_args_list[1][0][1]
    assert first_key.endswith("manifest.json")
    assert second_key.endswith("content.json")


# ---------------------------------------------------------------------------
# List AI content
# ---------------------------------------------------------------------------

@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_list_ai_content_empty(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.list_objects.return_value = []

    client = TestClient(app)
    resp = client.get("/books/42/ai-content/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_list_ai_content_with_entries(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    manifest_key = f"TestPub/books/TestBook/ai-content/{CONTENT_ID}/manifest.json"
    mock_obj = MagicMock()
    mock_obj.object_name = manifest_key
    mock_client.list_objects.return_value = [mock_obj]

    manifest_data = {**SAMPLE_MANIFEST, "content_id": CONTENT_ID}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(manifest_data).encode("utf-8")
    mock_client.get_object.return_value = mock_resp

    client = TestClient(app)
    resp = client.get("/books/42/ai-content/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["content_id"] == CONTENT_ID
    assert data[0]["activity_type"] == "listening_quiz"


# ---------------------------------------------------------------------------
# Get AI content
# ---------------------------------------------------------------------------

@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_get_ai_content_success(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    manifest_data = {**SAMPLE_MANIFEST, "content_id": CONTENT_ID}
    manifest_resp = MagicMock()
    manifest_resp.read.return_value = json.dumps(manifest_data).encode("utf-8")

    content_resp = MagicMock()
    content_resp.read.return_value = json.dumps(SAMPLE_CONTENT).encode("utf-8")

    mock_client.get_object.side_effect = [manifest_resp, content_resp]

    client = TestClient(app)
    resp = client.get(f"/books/42/ai-content/{CONTENT_ID}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["content_id"] == CONTENT_ID
    assert data["content"]["questions"][0]["id"] == "q1"


@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_get_ai_content_invalid_uuid(mock_repo, mock_auth, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book

    client = TestClient(app)
    resp = client.get("/books/42/ai-content/not-a-uuid", headers=auth_headers)
    assert resp.status_code == 400


@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_get_ai_content_not_found(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.get_object.side_effect = S3Error("NoSuchKey", "NoSuchKey", "", "", "", "", "")

    client = TestClient(app)
    resp = client.get(f"/books/42/ai-content/{CONTENT_ID}", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete AI content
# ---------------------------------------------------------------------------

@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_delete_ai_content_success(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    mock_obj1 = MagicMock()
    mock_obj1.object_name = f"TestPub/books/TestBook/ai-content/{CONTENT_ID}/manifest.json"
    mock_obj2 = MagicMock()
    mock_obj2.object_name = f"TestPub/books/TestBook/ai-content/{CONTENT_ID}/content.json"
    mock_client.list_objects.return_value = [mock_obj1, mock_obj2]

    client = TestClient(app)
    resp = client.delete(f"/books/42/ai-content/{CONTENT_ID}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["objects_removed"] == 2
    assert mock_client.remove_object.call_count == 2


@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_delete_ai_content_not_found(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.list_objects.return_value = []

    client = TestClient(app)
    resp = client.delete(f"/books/42/ai-content/{CONTENT_ID}", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Upload single audio
# ---------------------------------------------------------------------------

@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_upload_audio_success(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    audio_data = b"\xff\xfb\x90\x00" * 100
    client = TestClient(app)
    resp = client.put(
        f"/books/42/ai-content/{CONTENT_ID}/audio/q1.mp3",
        files={"file": ("q1.mp3", io.BytesIO(audio_data), "audio/mpeg")},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "q1.mp3"
    assert data["size"] == len(audio_data)


@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_upload_audio_invalid_filename(mock_repo, mock_auth, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book

    client = TestClient(app)
    resp = client.put(
        f"/books/42/ai-content/{CONTENT_ID}/audio/evil file.mp3",
        files={"file": ("evil.mp3", io.BytesIO(b"data"), "audio/mpeg")},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_upload_audio_non_mp3(mock_repo, mock_auth, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book

    client = TestClient(app)
    resp = client.put(
        f"/books/42/ai-content/{CONTENT_ID}/audio/file.wav",
        files={"file": ("file.wav", io.BytesIO(b"data"), "audio/wav")},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_upload_audio_content_not_found(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.stat_object.side_effect = S3Error("NoSuchKey", "NoSuchKey", "", "", "", "", "")

    audio_data = b"\xff\xfb\x90\x00" * 10
    client = TestClient(app)
    resp = client.put(
        f"/books/42/ai-content/{CONTENT_ID}/audio/q1.mp3",
        files={"file": ("q1.mp3", io.BytesIO(audio_data), "audio/mpeg")},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Batch audio upload
# ---------------------------------------------------------------------------

@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_batch_audio_upload_success(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    files = [
        ("files", ("q1.mp3", io.BytesIO(b"\xff" * 50), "audio/mpeg")),
        ("files", ("q2.mp3", io.BytesIO(b"\xff" * 60), "audio/mpeg")),
    ]
    client = TestClient(app)
    resp = client.post(
        f"/books/42/ai-content/{CONTENT_ID}/audio/batch",
        files=files,
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["uploaded"]) == 2
    assert len(data["failed"]) == 0


@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_batch_audio_upload_mixed(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    files = [
        ("files", ("q1.mp3", io.BytesIO(b"\xff" * 50), "audio/mpeg")),
        ("files", ("bad.wav", io.BytesIO(b"\xff" * 60), "audio/wav")),
    ]
    client = TestClient(app)
    resp = client.post(
        f"/books/42/ai-content/{CONTENT_ID}/audio/batch",
        files=files,
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["uploaded"]) == 1
    assert len(data["failed"]) == 1
    assert "bad.wav" in data["failed"]


# ---------------------------------------------------------------------------
# Stream audio
# ---------------------------------------------------------------------------

@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_stream_audio_full(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    audio_bytes = b"\xff\xfb\x90\x00" * 100
    mock_stat = MagicMock()
    mock_stat.size = len(audio_bytes)
    mock_client.stat_object.return_value = mock_stat

    mock_obj = MagicMock()
    mock_obj.stream.return_value = [audio_bytes]
    mock_client.get_object.return_value = mock_obj

    client = TestClient(app)
    resp = client.get(
        f"/books/42/ai-content/{CONTENT_ID}/audio/q1.mp3",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["accept-ranges"] == "bytes"
    assert resp.headers["content-type"] == "audio/mpeg"


@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_stream_audio_range(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    audio_bytes = b"\xff\xfb\x90\x00" * 100
    mock_stat = MagicMock()
    mock_stat.size = len(audio_bytes)
    mock_client.stat_object.return_value = mock_stat

    chunk = audio_bytes[:100]
    mock_obj = MagicMock()
    mock_obj.stream.return_value = [chunk]
    mock_client.get_object.return_value = mock_obj

    req_headers = {**auth_headers, "Range": "bytes=0-99"}
    client = TestClient(app)
    resp = client.get(
        f"/books/42/ai-content/{CONTENT_ID}/audio/q1.mp3",
        headers=req_headers,
    )
    assert resp.status_code == 206
    assert "content-range" in resp.headers
    assert resp.headers["content-range"] == f"bytes 0-99/{len(audio_bytes)}"


@patch("app.routers.ai_content.get_minio_client")
@patch("app.routers.ai_content._require_admin")
@patch("app.routers.ai_content._book_repository")
def test_stream_audio_not_found(mock_repo, mock_auth, mock_get_client, mock_book, auth_headers):
    mock_auth.return_value = 1
    mock_repo.get_by_id.return_value = mock_book
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.stat_object.side_effect = S3Error("NoSuchKey", "NoSuchKey", "", "", "", "", "")

    client = TestClient(app)
    resp = client.get(
        f"/books/42/ai-content/{CONTENT_ID}/audio/q1.mp3",
        headers=auth_headers,
    )
    assert resp.status_code == 404
