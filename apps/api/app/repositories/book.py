"""Database access helpers for book metadata."""

from __future__ import annotations

from app.models.book import Book
from app.repositories.base import BaseRepository


class BookRepository(BaseRepository[Book]):
    """Repository for interacting with book metadata records."""

    def __init__(self) -> None:
        super().__init__(model=Book)

    # CRUD helpers will be implemented in subsequent stories once API endpoints are added.
