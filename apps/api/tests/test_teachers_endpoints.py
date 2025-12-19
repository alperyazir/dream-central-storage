"""Integration-style tests for teacher material storage endpoints."""

from __future__ import annotations

import io
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db import get_db
from app.main import app
from app.services.storage import RelocationReport


@pytest.fixture(autouse=True)
def override_dependencies(monkeypatch):
    from app.routers import teachers

    monkeypatch.setattr(teachers, "_require_admin", lambda credentials, db: 1)

    fake_client = MagicMock()
    fake_client.list_objects.return_value = []
    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    def fake_get_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = fake_get_db

    yield

    app.dependency_overrides.pop(get_db, None)


def _auth_headers() -> dict[str, str]:
    token = create_access_token(subject="1")
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Upload Endpoint Tests
# ============================================================================


def test_upload_teacher_material_success(monkeypatch) -> None:
    """Test successful upload of a valid file."""
    from app.routers import teachers

    fake_client = MagicMock()
    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    file_content = b"test pdf content"

    response = client.post(
        "/teachers/teacher_123/upload",
        headers=_auth_headers(),
        files={"file": ("lesson.pdf", io.BytesIO(file_content), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["teacher_id"] == "teacher_123"
    assert body["filename"] == "lesson.pdf"
    assert body["path"] == "teacher_123/materials/lesson.pdf"
    assert body["size"] == len(file_content)
    assert body["content_type"] == "application/pdf"

    fake_client.put_object.assert_called_once()


def test_upload_teacher_material_invalid_mime_type(monkeypatch) -> None:
    """Test upload rejects files with unsupported MIME types."""
    from app.routers import teachers

    fake_client = MagicMock()
    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    file_content = b"executable content"

    response = client.post(
        "/teachers/teacher_123/upload",
        headers=_auth_headers(),
        files={"file": ("malware.exe", io.BytesIO(file_content), "application/x-msdownload")},
    )

    assert response.status_code == 415
    assert "not allowed" in response.json()["detail"].lower()
    fake_client.put_object.assert_not_called()


def test_upload_teacher_material_file_too_large(monkeypatch) -> None:
    """Test upload rejects files exceeding size limit."""
    from app.routers import teachers

    fake_client = MagicMock()
    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    # Create a file larger than 100MB (default limit is 104857600 bytes)
    file_content = b"x" * (104857600 + 1)

    response = client.post(
        "/teachers/teacher_123/upload",
        headers=_auth_headers(),
        files={"file": ("large_video.mp4", io.BytesIO(file_content), "video/mp4")},
    )

    assert response.status_code == 413
    assert "size exceeds" in response.json()["detail"].lower()
    fake_client.put_object.assert_not_called()


def test_upload_teacher_material_no_filename(monkeypatch) -> None:
    """Test upload rejects files without a filename."""
    from app.routers import teachers

    fake_client = MagicMock()
    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    file_content = b"test content"

    response = client.post(
        "/teachers/teacher_123/upload",
        headers=_auth_headers(),
        files={"file": ("", io.BytesIO(file_content), "application/pdf")},
    )

    # FastAPI returns 422 for validation errors (empty filename is invalid)
    assert response.status_code in [400, 422]


def test_upload_teacher_material_various_allowed_types(monkeypatch) -> None:
    """Test upload accepts all configured allowed MIME types."""
    from app.routers import teachers

    allowed_types = [
        ("document.pdf", "application/pdf"),
        ("notes.txt", "text/plain"),
        ("image.png", "image/png"),
        ("photo.jpeg", "image/jpeg"),
        ("audio.mp3", "audio/mpeg"),
        ("video.mp4", "video/mp4"),
        ("clip.webm", "video/webm"),
    ]

    for filename, mime_type in allowed_types:
        fake_client = MagicMock()
        monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

        client = TestClient(app)
        file_content = b"test content"

        response = client.post(
            "/teachers/teacher_123/upload",
            headers=_auth_headers(),
            files={"file": (filename, io.BytesIO(file_content), mime_type)},
        )

        assert response.status_code == 201, f"Failed for {mime_type}"
        fake_client.put_object.assert_called_once()


# ============================================================================
# List Materials Endpoint Tests
# ============================================================================


def test_list_teacher_materials_empty(monkeypatch) -> None:
    """Test listing materials when none exist."""
    from app.routers import teachers

    fake_client = MagicMock()
    fake_client.list_objects.return_value = []
    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.get(
        "/teachers/teacher_123/materials",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == "teacher_123/materials/"
    assert body["children"] == []


def test_list_teacher_materials_with_files(monkeypatch) -> None:
    """Test listing materials returns file tree."""
    from app.routers import teachers

    fake_client = MagicMock()
    fake_client.list_objects.return_value = [
        SimpleNamespace(object_name="teacher_123/materials/lesson.pdf", size=1024),
        SimpleNamespace(object_name="teacher_123/materials/audio/intro.mp3", size=2048),
    ]
    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.get(
        "/teachers/teacher_123/materials",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["path"] == "teacher_123/materials/"
    assert len(body["children"]) == 2


# ============================================================================
# Download Endpoint Tests
# ============================================================================


def test_download_teacher_material_success(monkeypatch) -> None:
    """Test successful file download."""
    from app.routers import teachers

    data = b"lesson content"
    fake_obj = MagicMock()
    fake_obj.stream.return_value = iter([data])
    fake_obj.close = MagicMock()
    fake_obj.release_conn = MagicMock()

    fake_client = MagicMock()
    fake_client.stat_object.return_value = SimpleNamespace(size=len(data), content_type="application/pdf")
    fake_client.get_object.return_value = fake_obj

    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.get(
        "/teachers/teacher_123/materials/lesson.pdf",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.content == data
    assert response.headers["accept-ranges"] == "bytes"
    assert response.headers["content-disposition"].startswith("inline;")
    fake_obj.close.assert_called_once()
    fake_obj.release_conn.assert_called_once()


def test_download_teacher_material_not_found(monkeypatch) -> None:
    """Test download returns 404 for missing file."""
    from app.routers import teachers
    from minio.error import S3Error

    fake_client = MagicMock()
    error = S3Error(
        code="NoSuchKey",
        message="Object not found",
        resource="/teachers/teacher_123/materials/missing.pdf",
        request_id="test",
        host_id="test",
        response=MagicMock(),
    )
    fake_client.stat_object.side_effect = error

    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.get(
        "/teachers/teacher_123/materials/missing.pdf",
        headers=_auth_headers(),
    )

    assert response.status_code == 404


def test_download_teacher_material_range_request(monkeypatch) -> None:
    """Test Range header returns 206 Partial Content."""
    from app.routers import teachers

    full_data = b"x" * 100
    partial_data = full_data[0:10]

    fake_obj = MagicMock()
    fake_obj.stream.return_value = iter([partial_data])
    fake_obj.close = MagicMock()
    fake_obj.release_conn = MagicMock()

    fake_client = MagicMock()
    fake_client.stat_object.return_value = SimpleNamespace(size=100, content_type="audio/mpeg")
    fake_client.get_object.return_value = fake_obj

    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    headers = _auth_headers()
    headers["Range"] = "bytes=0-9"

    response = client.get(
        "/teachers/teacher_123/materials/audio.mp3",
        headers=headers,
    )

    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 0-9/100"
    assert response.headers["content-length"] == "10"

    call_kwargs = fake_client.get_object.call_args
    assert call_kwargs.kwargs.get("offset") == 0
    assert call_kwargs.kwargs.get("length") == 10


def test_download_teacher_material_nested_path(monkeypatch) -> None:
    """Test downloading a file in a nested directory."""
    from app.routers import teachers

    data = b"nested content"
    fake_obj = MagicMock()
    fake_obj.stream.return_value = iter([data])
    fake_obj.close = MagicMock()
    fake_obj.release_conn = MagicMock()

    fake_client = MagicMock()
    fake_client.stat_object.return_value = SimpleNamespace(size=len(data), content_type="audio/mpeg")
    fake_client.get_object.return_value = fake_obj

    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.get(
        "/teachers/teacher_123/materials/unit1/audio/intro.mp3",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    # Verify the correct object key was constructed
    fake_client.stat_object.assert_called_once()
    call_args = fake_client.stat_object.call_args
    assert "teacher_123/materials/unit1/audio/intro.mp3" in call_args[0]


# ============================================================================
# Delete Endpoint Tests
# ============================================================================


def test_delete_teacher_material_success(monkeypatch) -> None:
    """Test successful soft-delete moves file to trash."""
    from app.routers import teachers

    relocation_report = RelocationReport(
        source_bucket="teachers",
        destination_bucket="trash",
        source_prefix="teacher_123/materials/lesson.pdf",
        destination_prefix="teachers/teacher_123/materials/lesson.pdf",
        objects_moved=1,
    )

    monkeypatch.setattr(
        teachers,
        "move_prefix_to_trash",
        lambda client, source_bucket, prefix, trash_bucket: relocation_report,
    )

    fake_client = MagicMock()
    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.delete(
        "/teachers/teacher_123/materials/lesson.pdf",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] is True
    assert body["teacher_id"] == "teacher_123"
    assert body["path"] == "lesson.pdf"
    assert body["objects_moved"] == 1


def test_delete_teacher_material_not_found(monkeypatch) -> None:
    """Test delete returns 404 when file doesn't exist."""
    from app.routers import teachers

    relocation_report = RelocationReport(
        source_bucket="teachers",
        destination_bucket="trash",
        source_prefix="teacher_123/materials/missing.pdf",
        destination_prefix="teachers/teacher_123/materials/missing.pdf",
        objects_moved=0,
    )

    monkeypatch.setattr(
        teachers,
        "move_prefix_to_trash",
        lambda client, source_bucket, prefix, trash_bucket: relocation_report,
    )

    fake_client = MagicMock()
    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.delete(
        "/teachers/teacher_123/materials/missing.pdf",
        headers=_auth_headers(),
    )

    assert response.status_code == 404


def test_delete_teacher_material_relocation_error(monkeypatch) -> None:
    """Test delete returns 502 on relocation error."""
    from app.routers import teachers
    from app.services.storage import RelocationError

    def raise_error(*args, **kwargs):
        raise RelocationError("Failed to move to trash")

    monkeypatch.setattr(teachers, "move_prefix_to_trash", raise_error)

    fake_client = MagicMock()
    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    response = client.delete(
        "/teachers/teacher_123/materials/lesson.pdf",
        headers=_auth_headers(),
    )

    assert response.status_code == 502


# ============================================================================
# Authentication Tests
# ============================================================================


def test_upload_requires_authentication() -> None:
    """Test upload endpoint requires authentication."""
    client = TestClient(app)
    file_content = b"test content"

    response = client.post(
        "/teachers/teacher_123/upload",
        files={"file": ("lesson.pdf", io.BytesIO(file_content), "application/pdf")},
    )

    assert response.status_code == 403


def test_list_requires_authentication() -> None:
    """Test list endpoint requires authentication."""
    client = TestClient(app)

    response = client.get("/teachers/teacher_123/materials")

    assert response.status_code == 403


def test_download_requires_authentication() -> None:
    """Test download endpoint requires authentication."""
    client = TestClient(app)

    response = client.get("/teachers/teacher_123/materials/lesson.pdf")

    assert response.status_code == 403


def test_delete_requires_authentication() -> None:
    """Test delete endpoint requires authentication."""
    client = TestClient(app)

    response = client.delete("/teachers/teacher_123/materials/lesson.pdf")

    assert response.status_code == 403


# ============================================================================
# Path Validation Tests
# ============================================================================


def test_upload_sanitizes_teacher_id(monkeypatch) -> None:
    """Test upload rejects teacher_id with invalid characters."""
    from app.routers import teachers

    fake_client = MagicMock()
    monkeypatch.setattr(teachers, "get_minio_client", lambda settings: fake_client)

    client = TestClient(app)
    file_content = b"test content"

    # Test with teacher_id containing a dot-dot traversal (sanitization check)
    response = client.post(
        "/teachers/..%2Fadmin/upload",  # URL-encoded ../
        headers=_auth_headers(),
        files={"file": ("lesson.pdf", io.BytesIO(file_content), "application/pdf")},
    )

    # The sanitization should reject invalid teacher_id (or return 404 if URL is normalized)
    # Either 400 (bad request) or 404 (not found after normalization) is acceptable
    assert response.status_code in [400, 404]
