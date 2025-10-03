"""Pydantic schemas used by the FastAPI application."""

from .auth import LoginRequest, TokenResponse
from .book import BookBase, BookCreate, BookRead, BookUpdate
from .storage import RestoreRequest, RestoreResponse, TrashEntryRead

__all__ = [
    "BookBase",
    "BookCreate",
    "BookRead",
    "BookUpdate",
    "RestoreRequest",
    "RestoreResponse",
    "TrashEntryRead",
    "LoginRequest",
    "TokenResponse",
]
