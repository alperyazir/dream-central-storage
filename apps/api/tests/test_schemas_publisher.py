"""Validation tests for publisher Pydantic schemas."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.publisher import Publisher, PublisherStatusEnum
from app.schemas.publisher import (
    PublisherBase,
    PublisherCreate,
    PublisherRead,
    PublisherUpdate,
    PublisherWithBooks,
)


def test_publisher_create_defaults() -> None:
    """Test PublisherCreate with minimal required fields."""
    payload = {"name": "Dream Press"}
    schema = PublisherCreate(**payload)
    assert schema.name == "Dream Press"
    assert schema.display_name is None
    assert schema.status == "active"


def test_publisher_create_full_payload() -> None:
    """Test PublisherCreate with all fields."""
    payload = {
        "name": "Dream Press",
        "display_name": "Dream Press Publishing",
        "description": "A great publisher",
        "logo_url": "https://example.com/logo.png",
        "contact_email": "contact@dreampress.com",
        "status": "inactive",
    }
    schema = PublisherCreate(**payload)
    assert schema.name == "Dream Press"
    assert schema.display_name == "Dream Press Publishing"
    assert schema.description == "A great publisher"
    assert schema.logo_url == "https://example.com/logo.png"
    assert schema.contact_email == "contact@dreampress.com"
    assert schema.status == "inactive"


def test_publisher_update_supports_partial_mutation() -> None:
    """Test PublisherUpdate with only some fields."""
    schema = PublisherUpdate(display_name="New Name")
    assert schema.display_name == "New Name"
    assert schema.name is None
    assert schema.status is None


def test_publisher_update_all_fields_optional() -> None:
    """Test that all fields in PublisherUpdate are optional."""
    schema = PublisherUpdate()
    assert schema.name is None
    assert schema.display_name is None
    assert schema.description is None
    assert schema.logo_url is None
    assert schema.contact_email is None
    assert schema.status is None


def test_publisher_read_serializes_from_orm() -> None:
    """Test PublisherRead can serialize from ORM model."""
    now = datetime.now(timezone.utc)
    publisher = Publisher(
        id=1,
        name="Dream Press",
        display_name="Dream Press Publishing",
        description="A great publisher",
        logo_url=None,
        contact_email="contact@dreampress.com",
        status="active",
    )
    publisher.created_at = now
    publisher.updated_at = now

    schema = PublisherRead.model_validate(publisher)
    assert schema.id == 1
    assert schema.name == "Dream Press"
    assert schema.display_name == "Dream Press Publishing"
    assert schema.status == "active"
    assert schema.created_at == now
    assert schema.updated_at == now


def test_publisher_with_books_empty_list() -> None:
    """Test PublisherWithBooks with no books."""
    now = datetime.now(timezone.utc)
    publisher = Publisher(
        id=1,
        name="Dream Press",
        display_name="Dream Press",
        status="active",
    )
    publisher.created_at = now
    publisher.updated_at = now
    # Manually set empty books list
    object.__setattr__(publisher, 'books', [])

    schema = PublisherWithBooks.model_validate(publisher)
    assert schema.id == 1
    assert schema.name == "Dream Press"
    assert schema.books == []


def test_publisher_base_name_required() -> None:
    """Test that name is required in PublisherBase."""
    with pytest.raises(ValueError):
        PublisherBase()  # type: ignore[call-arg]


def test_publisher_status_enum_values() -> None:
    """Test PublisherStatusEnum has expected values."""
    assert PublisherStatusEnum.ACTIVE.value == "active"
    assert PublisherStatusEnum.INACTIVE.value == "inactive"
    assert PublisherStatusEnum.SUSPENDED.value == "suspended"
