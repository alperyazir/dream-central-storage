"""Tests for publisher CRUD endpoints using mocks to avoid SQLite/JSONB issues."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.publisher import Publisher
from app.models.book import Book, BookStatusEnum


@pytest.fixture
def mock_publisher() -> Publisher:
    """Create a mock publisher object."""
    publisher = MagicMock(spec=Publisher)
    publisher.id = 1
    publisher.name = "Dream Press"
    publisher.display_name = "Dream Press Publishing"
    publisher.description = "A great publisher"
    publisher.logo_url = None
    publisher.contact_email = "contact@dreampress.com"
    publisher.status = "active"
    publisher.created_at = datetime(2025, 1, 1, 0, 0, 0)
    publisher.updated_at = datetime(2025, 1, 1, 0, 0, 0)
    publisher.books = []
    return publisher


@pytest.fixture
def mock_book(mock_publisher: Publisher) -> Book:
    """Create a mock book object."""
    book = MagicMock(spec=Book)
    book.id = 1
    book.publisher_id = 1
    book.book_name = "Test Book"
    book.book_title = "Test Book Title"
    book.book_cover = None
    book.language = "en"
    book.category = "fiction"
    book.version = None
    book.activity_count = 0
    book.activity_details = {}
    book.total_size = 0
    book.status = BookStatusEnum.PUBLISHED
    book.created_at = datetime(2025, 1, 1, 0, 0, 0)
    book.updated_at = datetime(2025, 1, 1, 0, 0, 0)
    book.publisher_rel = mock_publisher
    book.publisher = "Dream Press"
    return book


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return mock authorization headers."""
    return {"Authorization": "Bearer mock_token"}


# =============================================================================
# Authentication Tests
# =============================================================================


def test_create_publisher_requires_authentication() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/publishers/",
        json={"name": "Dream Press"},
    )
    assert response.status_code in {401, 403}


def test_list_publishers_requires_authentication() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/publishers/")
    assert response.status_code in {401, 403}


def test_get_publisher_requires_authentication() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/publishers/1")
    assert response.status_code in {401, 403}


def test_update_publisher_requires_authentication() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.put("/publishers/1", json={"name": "New Name"})
    assert response.status_code in {401, 403}


def test_delete_publisher_requires_authentication() -> None:
    client = TestClient(app, raise_server_exceptions=False)
    response = client.delete("/publishers/1")
    assert response.status_code in {401, 403}


# =============================================================================
# Create Publisher Tests
# =============================================================================


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_create_publisher_success(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.create.return_value = mock_publisher
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.post(
        "/publishers/",
        json={
            "name": "Dream Press",
            "display_name": "Dream Press Publishing",
            "description": "A great publisher",
            "contact_email": "contact@dreampress.com",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Dream Press"
    assert data["display_name"] == "Dream Press Publishing"
    assert data["status"] == "active"


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_create_publisher_duplicate_returns_409(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    auth_headers: dict[str, str],
) -> None:
    from sqlalchemy.exc import IntegrityError

    mock_auth.return_value = 1
    mock_repo.create.side_effect = IntegrityError("duplicate", None, None)
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.post(
        "/publishers/",
        json={"name": "Duplicate Press"},
        headers=auth_headers,
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


# =============================================================================
# List Publishers Tests
# =============================================================================


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_list_publishers_returns_all(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    publisher2 = MagicMock(spec=Publisher)
    publisher2.id = 2
    publisher2.name = "Another Press"
    publisher2.display_name = "Another Press"
    publisher2.description = None
    publisher2.logo_url = None
    publisher2.contact_email = None
    publisher2.status = "active"
    publisher2.created_at = datetime(2025, 1, 1, 0, 0, 0)
    publisher2.updated_at = datetime(2025, 1, 1, 0, 0, 0)

    mock_repo.list_paginated.return_value = [mock_publisher, publisher2]
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/publishers/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Dream Press"
    assert data[1]["name"] == "Another Press"


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_list_publishers_empty(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.list_paginated.return_value = []
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/publishers/", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_list_publishers_pagination_called(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.list_paginated.return_value = []
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/publishers/?skip=10&limit=5", headers=auth_headers)

    assert response.status_code == 200
    mock_repo.list_paginated.assert_called_once()
    call_args = mock_repo.list_paginated.call_args
    assert call_args.kwargs.get("skip") == 10 or call_args[1].get("skip") == 10 or (len(call_args[0]) > 1 and call_args[0][1] == 10)


# =============================================================================
# Get Publisher Tests
# =============================================================================


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_get_publisher_by_id(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.get.return_value = mock_publisher
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/publishers/1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Dream Press"


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_get_publisher_by_id_not_found(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.get.return_value = None
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/publishers/999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Publisher not found"


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_get_publisher_by_name(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.get_by_name.return_value = mock_publisher
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/publishers/by-name/Dream Press", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Dream Press"


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_get_publisher_by_name_not_found(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.get_by_name.return_value = None
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/publishers/by-name/NonExistent", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Publisher not found"


# =============================================================================
# Update Publisher Tests
# =============================================================================


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_update_publisher(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.get.return_value = mock_publisher

    updated_publisher = MagicMock(spec=Publisher)
    updated_publisher.id = 1
    updated_publisher.name = "Dream Press"
    updated_publisher.display_name = "Updated Display"
    updated_publisher.description = "Updated description"
    updated_publisher.logo_url = None
    updated_publisher.contact_email = "contact@dreampress.com"
    updated_publisher.status = "active"
    updated_publisher.created_at = datetime(2025, 1, 1, 0, 0, 0)
    updated_publisher.updated_at = datetime(2025, 1, 2, 0, 0, 0)

    mock_repo.update.return_value = updated_publisher
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.put(
        "/publishers/1",
        json={"display_name": "Updated Display", "description": "Updated description"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Updated Display"
    assert data["description"] == "Updated description"


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_update_publisher_not_found(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.get.return_value = None
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.put(
        "/publishers/999",
        json={"description": "New description"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Publisher not found"


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_update_publisher_empty_payload(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.get.return_value = mock_publisher
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.put(
        "/publishers/1",
        json={},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Dream Press"
    mock_repo.update.assert_not_called()


# =============================================================================
# Delete Publisher Tests
# =============================================================================


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_delete_publisher_soft_deletes(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.get.return_value = mock_publisher

    deleted_publisher = MagicMock(spec=Publisher)
    deleted_publisher.id = 1
    deleted_publisher.name = "Dream Press"
    deleted_publisher.display_name = "Dream Press Publishing"
    deleted_publisher.description = "A great publisher"
    deleted_publisher.logo_url = None
    deleted_publisher.contact_email = "contact@dreampress.com"
    deleted_publisher.status = "inactive"
    deleted_publisher.created_at = datetime(2025, 1, 1, 0, 0, 0)
    deleted_publisher.updated_at = datetime(2025, 1, 2, 0, 0, 0)

    mock_repo.update.return_value = deleted_publisher
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.delete("/publishers/1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inactive"
    mock_repo.update.assert_called_once()
    call_args = mock_repo.update.call_args
    assert call_args.kwargs.get("data") == {"status": "inactive"}


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_delete_publisher_not_found(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.get.return_value = None
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.delete("/publishers/999", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Publisher not found"


# =============================================================================
# Publisher Books Tests
# =============================================================================


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_get_publisher_books(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    mock_publisher: Publisher,
    mock_book: Book,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_publisher.books = [mock_book]
    mock_repo.get_with_books.return_value = mock_publisher
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/publishers/1/books", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["book_name"] == "Test Book"


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_get_publisher_books_empty(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_publisher.books = []
    mock_repo.get_with_books.return_value = mock_publisher
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/publishers/1/books", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


@patch("app.routers.publishers._require_admin")
@patch("app.routers.publishers._publisher_repository")
@patch("app.routers.publishers.get_db")
def test_get_publisher_books_not_found(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.get_with_books.return_value = None
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/publishers/999/books", headers=auth_headers)

    assert response.status_code == 404


# =============================================================================
# Books Filter by Publisher Tests
# =============================================================================


@patch("app.routers.books._require_admin")
@patch("app.routers.books._book_repository")
@patch("app.routers.books.get_db")
def test_list_books_filter_by_publisher_id(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    mock_book: Book,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.list_by_publisher_id.return_value = [mock_book]
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/books?publisher_id=1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    mock_repo.list_by_publisher_id.assert_called_once()


@patch("app.routers.books._require_admin")
@patch("app.routers.books._book_repository")
@patch("app.routers.books.get_db")
def test_list_books_no_filter(
    mock_get_db: MagicMock,
    mock_repo: MagicMock,
    mock_auth: MagicMock,
    mock_book: Book,
    auth_headers: dict[str, str],
) -> None:
    mock_auth.return_value = 1
    mock_repo.list_all_books.return_value = [mock_book]
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.get("/books", headers=auth_headers)

    assert response.status_code == 200
    mock_repo.list_all_books.assert_called_once()
    mock_repo.list_by_publisher_id.assert_not_called()
