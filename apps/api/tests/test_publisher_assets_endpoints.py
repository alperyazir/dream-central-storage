"""Tests for publisher asset management endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.publisher import Publisher


@pytest.fixture
def mock_publisher() -> Publisher:
    """Create a mock publisher object."""
    publisher = MagicMock(spec=Publisher)
    publisher.id = 1
    publisher.name = "Dream Press"
    publisher.display_name = "Dream Press Publishing"
    return publisher


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return mock authorization headers."""
    return {"Authorization": "Bearer mock_token"}


# =============================================================================
# Authentication Tests
# =============================================================================


def test_list_assets_requires_authentication() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/publishers/1/assets")
    assert response.status_code in {401, 403}


def test_list_asset_files_requires_authentication() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/publishers/1/assets/materials")
    assert response.status_code in {401, 403}


def test_upload_asset_requires_authentication() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/publishers/1/assets/materials")
    assert response.status_code in {401, 403}


def test_delete_asset_requires_authentication() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.delete("/publishers/1/assets/materials/file.pdf")
    assert response.status_code in {401, 403}


# =============================================================================
# Asset Type Validation Tests
# =============================================================================


@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_invalid_asset_type_format(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test that invalid asset type format returns 400."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher

    client = TestClient(app)

    # Invalid: uppercase letters
    response = client.get("/publishers/1/assets/Materials", headers=auth_headers)
    assert response.status_code == 400
    assert "Invalid asset type format" in response.json()["detail"]

    # Invalid: spaces
    response = client.get("/publishers/1/assets/my materials", headers=auth_headers)
    assert response.status_code == 400


@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_reserved_asset_type_names(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test that reserved asset type names are rejected."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher

    client = TestClient(app)

    # Test each reserved name
    for reserved_name in ["books", "trash", "temp"]:
        response = client.get(f"/publishers/1/assets/{reserved_name}", headers=auth_headers)
        assert response.status_code == 400
        assert "reserved name" in response.json()["detail"]


# =============================================================================
# List Assets Tests
# =============================================================================


@patch("app.routers.publishers.get_minio_client")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_list_assets_empty(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_minio: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test listing assets when publisher has no assets."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher
    mock_minio.return_value.list_objects.return_value = []

    client = TestClient(app)
    response = client.get("/publishers/1/assets", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["publisher_id"] == 1
    assert data["publisher_name"] == "Dream Press"
    assert data["asset_types"] == []


@patch("app.routers.publishers.get_minio_client")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_list_assets_with_multiple_types(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_minio: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test listing assets with multiple asset types."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher

    # Simulate MinIO objects for multiple asset types
    mock_objects = [
        SimpleNamespace(object_name="Dream Press/assets/materials/worksheet1.pdf", size=1000),
        SimpleNamespace(object_name="Dream Press/assets/materials/worksheet2.pdf", size=2000),
        SimpleNamespace(object_name="Dream Press/assets/logos/logo.png", size=5000),
    ]
    mock_minio.return_value.list_objects.return_value = mock_objects

    client = TestClient(app)
    response = client.get("/publishers/1/assets", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["publisher_id"] == 1
    assert len(data["asset_types"]) == 2

    # Check materials
    materials = next(at for at in data["asset_types"] if at["name"] == "materials")
    assert materials["file_count"] == 2
    assert materials["total_size"] == 3000

    # Check logos
    logos = next(at for at in data["asset_types"] if at["name"] == "logos")
    assert logos["file_count"] == 1
    assert logos["total_size"] == 5000


@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_list_assets_publisher_not_found(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    auth_headers: dict[str, str],
) -> None:
    """Test listing assets for non-existent publisher."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = None

    client = TestClient(app)
    response = client.get("/publishers/999/assets", headers=auth_headers)

    assert response.status_code == 404
    assert "Publisher not found" in response.json()["detail"]


# =============================================================================
# List Asset Type Files Tests
# =============================================================================


@patch("app.routers.publishers.get_minio_client")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_list_asset_type_files_empty(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_minio: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test listing files in empty asset type."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher
    mock_minio.return_value.list_objects.return_value = []

    client = TestClient(app)
    response = client.get("/publishers/1/assets/materials", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


@patch("app.routers.publishers.get_minio_client")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_list_asset_type_files_with_files(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_minio: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test listing files in asset type with files."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher

    # Simulate MinIO objects
    mock_objects = [
        SimpleNamespace(
            object_name="Dream Press/assets/materials/worksheet1.pdf",
            size=1000,
            content_type="application/pdf",
            last_modified=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        ),
        SimpleNamespace(
            object_name="Dream Press/assets/materials/audio.mp3",
            size=2000,
            content_type="audio/mpeg",
            last_modified=datetime(2025, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
        ),
    ]
    mock_minio.return_value.list_objects.return_value = mock_objects

    client = TestClient(app)
    response = client.get("/publishers/1/assets/materials", headers=auth_headers)

    assert response.status_code == 200
    files = response.json()
    assert len(files) == 2

    # Check first file
    assert files[0]["name"] == "worksheet1.pdf"
    assert files[0]["size"] == 1000
    assert files[0]["content_type"] == "application/pdf"

    # Check second file
    assert files[1]["name"] == "audio.mp3"
    assert files[1]["size"] == 2000
    assert files[1]["content_type"] == "audio/mpeg"


# =============================================================================
# Upload Asset Tests
# =============================================================================


@patch("app.routers.publishers.get_minio_client")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_upload_asset_file_success(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_minio: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test successful file upload to asset type."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher

    client = TestClient(app)
    file_content = b"PDF content here"
    files = {"file": ("worksheet.pdf", file_content, "application/pdf")}

    response = client.post(
        "/publishers/1/assets/materials",
        files=files,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "worksheet.pdf"
    assert data["path"] == "Dream Press/assets/materials/worksheet.pdf"
    assert data["size"] == len(file_content)
    assert data["content_type"] == "application/pdf"
    assert "last_modified" in data

    # Verify MinIO put_object was called
    mock_minio.return_value.put_object.assert_called_once()


@patch("app.routers.publishers.get_minio_client")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_upload_asset_to_new_type_creates_folder(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_minio: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test uploading to a new asset type creates the folder."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher

    client = TestClient(app)
    files = {"file": ("logo.png", b"PNG data", "image/png")}

    response = client.post(
        "/publishers/1/assets/logos",  # New asset type
        files=files,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["path"] == "Dream Press/assets/logos/logo.png"


# =============================================================================
# Delete Asset Tests
# =============================================================================


@patch("app.routers.publishers.move_prefix_to_trash")
@patch("app.routers.publishers.get_minio_client")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_delete_asset_file_success(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_minio: MagicMock,
    mock_move_to_trash: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test successful deletion of asset file."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher

    # Mock the relocation report
    from app.services import RelocationReport
    mock_move_to_trash.return_value = RelocationReport(
        source_bucket="publishers",
        destination_bucket="trash",
        source_prefix="Dream Press/assets/materials/worksheet.pdf",
        destination_prefix="trash/publishers/Dream Press/assets/materials/worksheet.pdf",
        objects_moved=1,
    )

    client = TestClient(app)
    response = client.delete(
        "/publishers/1/assets/materials/worksheet.pdf",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "File moved to trash"
    assert data["objects_moved"] == 1
    assert "trash_key" in data


@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_delete_asset_publisher_not_found(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    auth_headers: dict[str, str],
) -> None:
    """Test deleting asset for non-existent publisher."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = None

    client = TestClient(app)
    response = client.delete(
        "/publishers/999/assets/materials/file.pdf",
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert "Publisher not found" in response.json()["detail"]


# =============================================================================
# Publisher Logo Endpoint Tests
# =============================================================================


def test_get_publisher_logo_requires_authentication() -> None:
    """Test that logo endpoint requires authentication."""
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/publishers/1/logo")
    assert response.status_code in {401, 403}


@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_get_publisher_logo_publisher_not_found(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    auth_headers: dict[str, str],
) -> None:
    """Test logo endpoint returns 404 for non-existent publisher."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = None

    client = TestClient(app)
    response = client.get("/publishers/999/logo", headers=auth_headers)

    assert response.status_code == 404
    assert "Publisher not found" in response.json()["detail"]


@patch("app.routers.publishers.get_minio_client")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_get_publisher_logo_not_found(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_minio: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test logo endpoint returns 404 when no logo exists."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher
    mock_minio.return_value.list_objects.return_value = []

    client = TestClient(app)
    response = client.get("/publishers/1/logo", headers=auth_headers)

    assert response.status_code == 404
    assert "Logo not found" in response.json()["detail"]


@patch("app.routers.publishers.get_minio_client")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_get_publisher_logo_success(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_minio: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test successful logo retrieval."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher

    # Mock list_objects to return a logo file
    mock_logo_object = SimpleNamespace(
        object_name="Dream Press/assets/logos/logo.png",
        size=5000,
    )
    mock_minio.return_value.list_objects.return_value = [mock_logo_object]

    # Mock get_object and stat_object
    mock_response = MagicMock()
    mock_response.read.return_value = b"PNG image data"
    mock_response.__iter__ = lambda self: iter([b"PNG image data"])
    mock_minio.return_value.get_object.return_value = mock_response

    mock_stat = SimpleNamespace(
        content_type="image/png",
        size=5000,
    )
    mock_minio.return_value.stat_object.return_value = mock_stat

    client = TestClient(app)
    response = client.get("/publishers/1/logo", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-disposition"] == 'inline; filename="logo.png"'


@patch("app.routers.publishers.get_minio_client")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers._require_admin")
def test_get_publisher_logo_picks_first_file(
    mock_require_admin: MagicMock,
    mock_repo: MagicMock,
    mock_minio: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test that logo endpoint picks the first file when multiple exist."""
    mock_require_admin.return_value = 1
    mock_repo.get.return_value = mock_publisher

    # Mock list_objects to return multiple logo files
    mock_logo_objects = [
        SimpleNamespace(object_name="Dream Press/assets/logos/logo.png", size=5000),
        SimpleNamespace(object_name="Dream Press/assets/logos/logo-dark.png", size=6000),
    ]
    mock_minio.return_value.list_objects.return_value = mock_logo_objects

    # Mock get_object and stat_object
    mock_response = MagicMock()
    mock_response.__iter__ = lambda self: iter([b"PNG image data"])
    mock_minio.return_value.get_object.return_value = mock_response

    mock_stat = SimpleNamespace(
        content_type="image/png",
        size=5000,
    )
    mock_minio.return_value.stat_object.return_value = mock_stat

    client = TestClient(app)
    response = client.get("/publishers/1/logo", headers=auth_headers)

    assert response.status_code == 200
    # Should return the first file (logo.png)
    assert response.headers["content-disposition"] == 'inline; filename="logo.png"'
    # Verify get_object was called with the first file
    mock_minio.return_value.get_object.assert_called_once()
    call_args = mock_minio.return_value.get_object.call_args
    assert "logo.png" in call_args[0][1]
