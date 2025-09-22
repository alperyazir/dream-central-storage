"""Validation tests for book Pydantic schemas."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.book import Book, BookStatusEnum
from app.schemas.book import BookCreate, BookRead, BookUpdate


def test_book_create_defaults() -> None:
    payload = {
        "publisher": "Dream Press",
        "book_name": "Midnight Stories",
        "language": "en",
        "category": "fiction",
    }
    schema = BookCreate(**payload)
    assert schema.status is BookStatusEnum.DRAFT
    assert schema.version is None


def test_book_update_supports_partial_mutation() -> None:
    schema = BookUpdate(status=BookStatusEnum.PUBLISHED)
    assert schema.status is BookStatusEnum.PUBLISHED
    assert schema.publisher is None


def test_book_update_rejects_invalid_status() -> None:
    with pytest.raises(ValueError):
        BookUpdate(status="invalid")  # type: ignore[arg-type]


def test_book_read_serializes_from_orm() -> None:
    book = Book(
        id=1,
        publisher="Dream Press",
        book_name="Midnight Stories",
        language="en",
        category="fiction",
        version=None,
        status=BookStatusEnum.DRAFT,
    )
    now = datetime.now(timezone.utc)
    book.created_at = now
    book.updated_at = now

    schema = BookRead.model_validate(book)
    assert schema.id == 1
    assert schema.created_at == now
    assert schema.status is BookStatusEnum.DRAFT
