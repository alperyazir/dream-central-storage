"""Pydantic schemas used by the FastAPI application."""

from .book import BookBase, BookCreate, BookRead, BookUpdate

__all__ = ["BookBase", "BookCreate", "BookRead", "BookUpdate"]
