"""Tests for update_book_metadata.py script."""

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.models.book import BookStatusEnum


def test_collect_activity_details():
    """Test activity details collection from config.json."""
    from update_book_metadata import _collect_activity_details

    config_data = {
        "chapters": [
            {
                "pages": [
                    {"activity": {"type": "reading"}},
                    {"activity": {"type": "quiz"}},
                    {"activity": {"type": "reading"}},
                ]
            },
            {
                "pages": [
                    {"activity": {"type": "video"}},
                ]
            },
        ]
    }

    result = _collect_activity_details(config_data)

    assert result == {"reading": 2, "quiz": 1, "video": 1}


def test_collect_activity_details_nested():
    """Test activity details collection with nested structures."""
    from update_book_metadata import _collect_activity_details

    config_data = {
        "units": [
            {
                "lessons": [
                    {
                        "activity": {"type": "exercise"},
                        "subactivities": [{"activity": {"type": "practice"}}],
                    }
                ]
            }
        ]
    }

    result = _collect_activity_details(config_data)

    assert result == {"exercise": 1, "practice": 1}


def test_calculate_book_metadata_success():
    """Test metadata calculation for a book."""
    from update_book_metadata import calculate_book_metadata

    # Create mock MinIO client
    mock_client = MagicMock()

    # Mock objects list
    mock_obj_1 = MagicMock()
    mock_obj_1.object_name = "test-publisher/books/test-book/page1.html"
    mock_obj_1.size = 1024

    mock_obj_2 = MagicMock()
    mock_obj_2.object_name = "test-publisher/books/test-book/config.json"
    mock_obj_2.size = 512

    mock_client.list_objects.return_value = [mock_obj_1, mock_obj_2]

    # Mock config.json response
    config_data = {"chapters": [{"pages": [{"activity": {"type": "reading"}}]}]}
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(config_data).encode()
    mock_client.get_object.return_value = mock_response

    # Calculate metadata
    total_size, activity_details = calculate_book_metadata(
        mock_client, "publishers", "test-publisher/books/test-book/"
    )

    assert total_size == 1536  # 1024 + 512
    assert activity_details == {"reading": 1}
    mock_client.list_objects.assert_called_once_with(
        "publishers", prefix="test-publisher/books/test-book/", recursive=True
    )


def test_calculate_book_metadata_no_config():
    """Test metadata calculation when no config.json exists."""
    from update_book_metadata import calculate_book_metadata

    mock_client = MagicMock()

    mock_obj = MagicMock()
    mock_obj.object_name = "test-publisher/books/test-book/page1.html"
    mock_obj.size = 2048

    mock_client.list_objects.return_value = [mock_obj]

    total_size, activity_details = calculate_book_metadata(
        mock_client, "publishers", "test-publisher/books/test-book/"
    )

    assert total_size == 2048
    assert activity_details == {}


def test_calculate_book_metadata_invalid_config():
    """Test metadata calculation with invalid config.json."""
    from update_book_metadata import calculate_book_metadata

    mock_client = MagicMock()

    mock_obj_1 = MagicMock()
    mock_obj_1.object_name = "test-publisher/books/test-book/page1.html"
    mock_obj_1.size = 1024

    mock_obj_2 = MagicMock()
    mock_obj_2.object_name = "test-publisher/books/test-book/config.json"
    mock_obj_2.size = 256

    mock_client.list_objects.return_value = [mock_obj_1, mock_obj_2]

    # Mock invalid JSON response
    mock_response = MagicMock()
    mock_response.read.return_value = b"invalid json"
    mock_client.get_object.return_value = mock_response

    total_size, activity_details = calculate_book_metadata(
        mock_client, "publishers", "test-publisher/books/test-book/"
    )

    # Should still calculate size, but no activity details
    assert total_size == 1280
    assert activity_details == {}


def test_main_updates_books():
    """Test main function updates book metadata correctly."""
    from update_book_metadata import main

    # Create mock publisher
    mock_publisher = MagicMock()
    mock_publisher.id = 1
    mock_publisher.name = "test-publisher"

    # Create mock book
    mock_book = MagicMock()
    mock_book.publisher_id = 1
    mock_book.book_name = "test-book"
    mock_book.book_title = "Test Book Title"
    mock_book.language = "en"
    mock_book.status = BookStatusEnum.PUBLISHED
    type(mock_book).publisher = PropertyMock(return_value="test-publisher")
    mock_book.total_size = None
    mock_book.activity_details = None

    # Mock database session
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.options.return_value.filter.return_value.all.return_value = [mock_book]
    mock_session.query.return_value = mock_query

    # Mock MinIO client
    with patch("update_book_metadata.get_minio_client") as mock_get_client:
        mock_client = MagicMock()

        mock_obj = MagicMock()
        mock_obj.object_name = "test-publisher/books/test-book/config.json"
        mock_obj.size = 512

        mock_client.list_objects.return_value = [mock_obj]

        config_data = {"chapters": [{"pages": [{"activity": {"type": "quiz"}}]}]}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(config_data).encode()
        mock_client.get_object.return_value = mock_response

        mock_get_client.return_value = mock_client

        # Mock SessionLocal
        with patch("update_book_metadata.SessionLocal") as mock_session_local:
            mock_session_local.return_value = mock_session

            # Run main
            main()

            # Verify book was updated
            assert mock_book.total_size == 512
            assert mock_book.activity_details == {"quiz": 1}
            mock_session.commit.assert_called()


def test_main_uses_publisher_relationship():
    """Test that main function properly uses publisher relationship."""
    from update_book_metadata import main

    # Create mock book with publisher relationship
    mock_book = MagicMock()
    mock_book.publisher_id = 1
    mock_book.book_name = "brains"
    mock_book.book_title = "Brains English"
    mock_book.language = "en"
    mock_book.status = BookStatusEnum.PUBLISHED
    type(mock_book).publisher = PropertyMock(return_value="universal-elt")

    # Mock database session
    mock_session = MagicMock()
    mock_query = MagicMock()
    mock_query.options.return_value.filter.return_value.all.return_value = [mock_book]
    mock_session.query.return_value = mock_query

    with patch("update_book_metadata.get_minio_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.list_objects.return_value = []
        mock_get_client.return_value = mock_client

        with patch("update_book_metadata.SessionLocal") as mock_session_local:
            mock_session_local.return_value = mock_session

            # Run main
            main()

            # Verify the correct prefix was used (publisher name from relationship)
            mock_client.list_objects.assert_called()
            call_args = mock_client.list_objects.call_args
            assert "universal-elt/books/brains/" in str(call_args)
