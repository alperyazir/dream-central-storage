"""ORM model for book metadata."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BookStatusEnum(str, enum.Enum):
    """Lifecycle states for book metadata records."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Book(Base):
    """Represents a book metadata record persisted in PostgreSQL."""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    book_name: Mapped[str] = mapped_column(String(255), nullable=False)
    book_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    book_cover: Mapped[str | None] = mapped_column(String(512), nullable=True)
    activity_count: Mapped[int | None] = mapped_column(nullable=True)
    activity_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    total_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[BookStatusEnum] = mapped_column(
        Enum(BookStatusEnum, name="book_status", native_enum=False),
        nullable=False,
        default=BookStatusEnum.DRAFT,
        server_default=BookStatusEnum.DRAFT.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
