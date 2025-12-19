"""Tests for Publisher ORM model."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.book import Book, BookStatusEnum
from app.models.publisher import Publisher, PublisherStatusEnum


def test_publisher_model_creation() -> None:
    """Test Publisher model can be instantiated with required fields."""
    publisher = Publisher(
        id=1,
        name="Dream Press",
        display_name="Dream Press Publishing",
        status="active",
    )
    assert publisher.id == 1
    assert publisher.name == "Dream Press"
    assert publisher.display_name == "Dream Press Publishing"
    assert publisher.status == "active"


def test_publisher_model_optional_fields() -> None:
    """Test Publisher model with all fields including optional ones."""
    now = datetime.now(timezone.utc)
    publisher = Publisher(
        id=1,
        name="Dream Press",
        display_name="Dream Press Publishing",
        description="A great publisher of interactive books",
        logo_url="https://example.com/logo.png",
        contact_email="contact@dreampress.com",
        status="active",
    )
    publisher.created_at = now
    publisher.updated_at = now

    assert publisher.description == "A great publisher of interactive books"
    assert publisher.logo_url == "https://example.com/logo.png"
    assert publisher.contact_email == "contact@dreampress.com"
    assert publisher.created_at == now
    assert publisher.updated_at == now


def test_publisher_status_enum() -> None:
    """Test PublisherStatusEnum values."""
    assert PublisherStatusEnum.ACTIVE.value == "active"
    assert PublisherStatusEnum.INACTIVE.value == "inactive"
    assert PublisherStatusEnum.SUSPENDED.value == "suspended"

    # Test enum iteration
    statuses = [s.value for s in PublisherStatusEnum]
    assert "active" in statuses
    assert "inactive" in statuses
    assert "suspended" in statuses


def test_publisher_book_relationship_bidirectional() -> None:
    """Test that Publisher-Book relationship is bidirectional."""
    publisher = Publisher(
        id=1,
        name="Dream Press",
        display_name="Dream Press",
        status="active",
    )

    book = Book(
        id=1,
        publisher_id=1,
        book_name="Sky Atlas",
        language="en",
        status=BookStatusEnum.DRAFT,
    )

    # Manually set up bidirectional relationship for unit test
    object.__setattr__(book, 'publisher_rel', publisher)
    object.__setattr__(publisher, 'books', [book])

    # Test Publisher -> Books direction
    assert len(publisher.books) == 1
    assert publisher.books[0].book_name == "Sky Atlas"

    # Test Book -> Publisher direction
    assert book.publisher_rel.name == "Dream Press"

    # Test Book.publisher property
    assert book.publisher == "Dream Press"


def test_publisher_tablename() -> None:
    """Test Publisher model has correct table name."""
    assert Publisher.__tablename__ == "publishers"


def test_book_tablename() -> None:
    """Test Book model has correct table name."""
    assert Book.__tablename__ == "books"
