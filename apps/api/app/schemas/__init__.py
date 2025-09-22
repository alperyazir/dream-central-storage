"""Pydantic schemas used by the FastAPI application."""

from .auth import LoginRequest, TokenResponse
from .book import BookBase, BookCreate, BookRead, BookUpdate

__all__ = [
    "BookBase",
    "BookCreate",
    "BookRead",
    "BookUpdate",
    "LoginRequest",
    "TokenResponse",
]
