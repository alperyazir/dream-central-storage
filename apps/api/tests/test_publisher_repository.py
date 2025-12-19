"""Tests for PublisherRepository database access methods."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models.publisher import Publisher
from app.repositories.publisher import PublisherRepository


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def repository() -> PublisherRepository:
    """Create a PublisherRepository instance."""
    return PublisherRepository()


def test_repository_model_type(repository: PublisherRepository) -> None:
    """Test that repository has correct model type."""
    assert repository.model is Publisher


def test_list_all_returns_all_publishers(
    repository: PublisherRepository,
    mock_session: MagicMock,
) -> None:
    """Test list_all() returns all publisher records."""
    publisher1 = Publisher(id=1, name="Dream Press", status="active")
    publisher2 = Publisher(id=2, name="Nightfall", status="active")

    mock_session.scalars.return_value.all.return_value = [publisher1, publisher2]

    result = repository.list_all(mock_session)

    assert len(result) == 2
    assert result[0].name == "Dream Press"
    assert result[1].name == "Nightfall"
    mock_session.scalars.assert_called_once()


def test_get_by_name_found(
    repository: PublisherRepository,
    mock_session: MagicMock,
) -> None:
    """Test get_by_name() returns publisher when found."""
    publisher = Publisher(id=1, name="Dream Press", status="active")

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = publisher
    mock_session.execute.return_value = mock_result

    result = repository.get_by_name(mock_session, "Dream Press")

    assert result is not None
    assert result.name == "Dream Press"


def test_get_by_name_not_found(
    repository: PublisherRepository,
    mock_session: MagicMock,
) -> None:
    """Test get_by_name() returns None when not found."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    result = repository.get_by_name(mock_session, "Nonexistent Press")

    assert result is None


def test_get_or_create_by_name_existing(
    repository: PublisherRepository,
    mock_session: MagicMock,
) -> None:
    """Test get_or_create_by_name() returns existing publisher."""
    existing_publisher = Publisher(id=1, name="Dream Press", status="active")

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = existing_publisher
    mock_session.execute.return_value = mock_result

    result = repository.get_or_create_by_name(mock_session, "Dream Press")

    assert result is existing_publisher
    assert result.id == 1
    # Should not call add since publisher exists
    mock_session.add.assert_not_called()


def test_get_or_create_by_name_new(
    repository: PublisherRepository,
    mock_session: MagicMock,
) -> None:
    """Test get_or_create_by_name() creates new publisher when not found."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    result = repository.get_or_create_by_name(mock_session, "New Press")

    assert result.name == "New Press"
    assert result.display_name == "New Press"
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once()


def test_get_with_books_returns_publisher(
    repository: PublisherRepository,
    mock_session: MagicMock,
) -> None:
    """Test get_with_books() returns publisher with eager-loaded books."""
    publisher = Publisher(id=1, name="Dream Press", status="active")

    mock_session.scalars.return_value.first.return_value = publisher

    result = repository.get_with_books(mock_session, publisher_id=1)

    assert result is not None
    assert result.name == "Dream Press"
    mock_session.scalars.assert_called_once()


def test_get_with_books_not_found(
    repository: PublisherRepository,
    mock_session: MagicMock,
) -> None:
    """Test get_with_books() returns None when publisher not found."""
    mock_session.scalars.return_value.first.return_value = None

    result = repository.get_with_books(mock_session, publisher_id=999)

    assert result is None


def test_create_persists_publisher(
    repository: PublisherRepository,
    mock_session: MagicMock,
) -> None:
    """Test create() persists a new publisher."""
    data = {
        "name": "Dream Press",
        "display_name": "Dream Press Publishing",
        "status": "active",
    }

    result = repository.create(mock_session, data=data)

    assert result.name == "Dream Press"
    assert result.display_name == "Dream Press Publishing"
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once()
    mock_session.commit.assert_called_once()


def test_update_modifies_fields(
    repository: PublisherRepository,
    mock_session: MagicMock,
) -> None:
    """Test update() modifies publisher fields."""
    publisher = Publisher(id=1, name="Dream Press", status="active")

    result = repository.update(
        mock_session,
        publisher,
        data={"display_name": "Updated Name", "status": "inactive"},
    )

    assert result.display_name == "Updated Name"
    assert result.status == "inactive"
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once()
    mock_session.commit.assert_called_once()


def test_delete_removes_publisher(
    repository: PublisherRepository,
    mock_session: MagicMock,
) -> None:
    """Test delete() removes a publisher."""
    publisher = Publisher(id=1, name="Dream Press", status="active")

    repository.delete(mock_session, publisher)

    mock_session.delete.assert_called_once_with(publisher)
    mock_session.commit.assert_called_once()
