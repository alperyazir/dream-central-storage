"""Tests for book webhook triggers."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import ANY, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.book import Book, BookStatusEnum
from app.models.publisher import Publisher
from app.models.webhook import WebhookEventType


@pytest.fixture
def mock_publisher() -> Publisher:
    """Create a mock publisher object."""
    publisher = MagicMock(spec=Publisher)
    publisher.id = 1
    publisher.name = "Dream Press"
    publisher.display_name = "Dream Press Publishing"
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
# Book Webhook Tests
# =============================================================================


@patch("app.routers.books._trigger_webhook")
@patch("app.routers.books._require_admin")
@patch("app.routers.books._book_repository")
@patch("app.routers.books._publisher_repository")
@patch("app.routers.books.get_db")
def test_create_book_triggers_webhook(
    mock_get_db: MagicMock,
    mock_publisher_repo: MagicMock,
    mock_book_repo: MagicMock,
    mock_auth: MagicMock,
    mock_trigger_webhook: MagicMock,
    mock_book: Book,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test that creating a book triggers a webhook."""
    mock_auth.return_value = 1
    mock_publisher_repo.get_or_create_by_name.return_value = mock_publisher
    mock_book_repo.create.return_value = mock_book
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.post(
        "/books",
        json={
            "publisher": "Dream Press",
            "book_name": "Test Book",
            "language": "en",
            "category": "fiction",
            "status": "published",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    # Verify webhook was scheduled (called via background_tasks)
    mock_trigger_webhook.assert_called_once_with(
        mock_book.id, WebhookEventType.BOOK_CREATED
    )


@patch("app.routers.books._trigger_webhook")
@patch("app.routers.books._require_admin")
@patch("app.routers.books._book_repository")
@patch("app.routers.books._publisher_repository")
@patch("app.routers.books.get_db")
def test_update_book_triggers_webhook(
    mock_get_db: MagicMock,
    mock_publisher_repo: MagicMock,
    mock_book_repo: MagicMock,
    mock_auth: MagicMock,
    mock_trigger_webhook: MagicMock,
    mock_book: Book,
    mock_publisher: Publisher,
    auth_headers: dict[str, str],
) -> None:
    """Test that updating a book triggers a webhook."""
    mock_auth.return_value = 1
    mock_book_repo.get_by_id.return_value = mock_book
    mock_publisher_repo.get_or_create_by_name.return_value = mock_publisher

    updated_book = MagicMock(spec=Book)
    updated_book.id = 1
    updated_book.book_name = "Test Book"
    updated_book.book_title = "Updated Title"
    updated_book.book_cover = None
    updated_book.publisher_id = 1
    updated_book.publisher = "Dream Press"
    updated_book.language = "en"
    updated_book.category = "fiction"
    updated_book.version = None
    updated_book.activity_count = 0
    updated_book.activity_details = {}
    updated_book.total_size = 0
    updated_book.status = BookStatusEnum.PUBLISHED
    updated_book.created_at = datetime(2025, 1, 1, 0, 0, 0)
    updated_book.updated_at = datetime(2025, 1, 2, 0, 0, 0)

    mock_book_repo.update.return_value = updated_book
    mock_get_db.return_value = MagicMock()

    client = TestClient(app)
    response = client.put(
        "/books/1",
        json={"book_title": "Updated Title"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    mock_trigger_webhook.assert_called_once_with(
        1, WebhookEventType.BOOK_UPDATED
    )


@patch("app.routers.books.move_prefix_to_trash")
@patch("app.routers.books.get_minio_client")
@patch("app.routers.books._trigger_webhook")
@patch("app.routers.books._require_admin")
@patch("app.routers.books._book_repository")
@patch("app.routers.books.get_db")
def test_delete_book_triggers_webhook(
    mock_get_db: MagicMock,
    mock_book_repo: MagicMock,
    mock_auth: MagicMock,
    mock_trigger_webhook: MagicMock,
    mock_minio: MagicMock,
    mock_move_to_trash: MagicMock,
    mock_book: Book,
    auth_headers: dict[str, str],
) -> None:
    """Test that deleting a book triggers a webhook."""
    from app.services import RelocationReport

    mock_auth.return_value = 1
    mock_book_repo.get_by_id.return_value = mock_book

    archived_book = MagicMock(spec=Book)
    archived_book.id = 1
    archived_book.book_name = "Test Book"
    archived_book.book_title = "Test Book Title"
    archived_book.book_cover = None
    archived_book.publisher_id = 1
    archived_book.publisher = "Dream Press"
    archived_book.language = "en"
    archived_book.category = "fiction"
    archived_book.version = None
    archived_book.activity_count = 0
    archived_book.activity_details = {}
    archived_book.total_size = 0
    archived_book.status = BookStatusEnum.ARCHIVED
    archived_book.created_at = datetime(2025, 1, 1, 0, 0, 0)
    archived_book.updated_at = datetime(2025, 1, 1, 0, 0, 0)

    mock_book_repo.archive.return_value = archived_book
    mock_get_db.return_value = MagicMock()

    # Mock the relocation report
    mock_move_to_trash.return_value = RelocationReport(
        source_bucket="publishers",
        destination_bucket="trash",
        source_prefix="Dream Press/books/Test Book/",
        destination_prefix="trash/publishers/Dream Press/books/Test Book/",
        objects_moved=1,
    )

    client = TestClient(app)
    response = client.delete("/books/1", headers=auth_headers)

    assert response.status_code == 200
    mock_trigger_webhook.assert_called_once_with(
        1, WebhookEventType.BOOK_DELETED
    )
