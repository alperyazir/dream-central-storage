"""Pydantic schemas for book metadata payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.book import BookStatusEnum


class BookBase(BaseModel):
    """Shared attributes required for book metadata operations."""

    publisher: str = Field(..., max_length=255)
    book_name: str = Field(..., max_length=255)  # Derived from ZIP filename
    book_title: str | None = Field(default=None, max_length=255)  # From config.json
    book_cover: str | None = Field(default=None, max_length=512)
    activity_count: int | None = Field(default=None)
    activity_details: dict | None = Field(default=None)
    total_size: int | None = Field(default=None)
    language: str = Field(default="en", max_length=64)  # Defaults to "en" if not specified
    category: str | None = Field(default=None, max_length=128)
    status: BookStatusEnum = Field(default=BookStatusEnum.DRAFT)


class BookCreate(BookBase):
    """Payload for creating a new book record."""

    pass


class BookUpdate(BaseModel):
    """Payload for updating existing book metadata."""

    publisher: str | None = Field(default=None, max_length=255)
    book_name: str | None = Field(default=None, max_length=255)
    book_title: str | None = Field(default=None, max_length=255)
    book_cover: str | None = Field(default=None, max_length=512)
    activity_count: int | None = Field(default=None)
    activity_details: dict | None = Field(default=None)
    total_size: int | None = Field(default=None)
    language: str | None = Field(default="en", max_length=64)  # Defaults to "en"
    category: str | None = Field(default=None, max_length=128)
    status: BookStatusEnum | None = Field(default=None)


class BookRead(BookBase):
    """Representation returned by the API for persisted book records."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
