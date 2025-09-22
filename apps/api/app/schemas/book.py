"""Pydantic schemas for book metadata payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.book import BookStatusEnum


class BookBase(BaseModel):
    """Shared attributes required for book metadata operations."""

    publisher: str = Field(..., max_length=255)
    book_name: str = Field(..., max_length=255)
    language: str = Field(..., max_length=64)
    category: str = Field(..., max_length=128)
    version: str | None = Field(default=None, max_length=64)
    status: BookStatusEnum = Field(default=BookStatusEnum.DRAFT)


class BookCreate(BookBase):
    """Payload for creating a new book record."""

    pass


class BookUpdate(BaseModel):
    """Payload for updating existing book metadata."""

    publisher: str | None = Field(default=None, max_length=255)
    book_name: str | None = Field(default=None, max_length=255)
    language: str | None = Field(default=None, max_length=64)
    category: str | None = Field(default=None, max_length=128)
    version: str | None = Field(default=None, max_length=64)
    status: BookStatusEnum | None = Field(default=None)


class BookRead(BookBase):
    """Representation returned by the API for persisted book records."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
