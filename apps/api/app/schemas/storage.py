"""Pydantic schemas for storage-related endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.book import BookRead


class TrashEntryRead(BaseModel):
    """Represents an aggregated trash entry available for restoration."""

    key: str = Field(..., description="Full key within the trash bucket including trailing slash")
    bucket: str = Field(..., description="Original bucket the content belonged to")
    path: str = Field(..., description="Original path within the bucket")
    item_type: Literal["book", "app", "unknown"] = Field(default="unknown")
    object_count: int = Field(..., ge=0)
    total_size: int = Field(..., ge=0)
    metadata: dict[str, str] | None = None


class RestoreRequest(BaseModel):
    """Request payload for restoring an item from the trash bucket."""

    key: str = Field(..., description="Key identifying the trash entry to restore")


class RestoreResponse(BaseModel):
    """Response returned after initiating a restore operation."""

    restored_key: str
    objects_moved: int
    item_type: Literal["book", "app", "unknown"]
    book: BookRead | None = None


__all__ = [
    "TrashEntryRead",
    "RestoreRequest",
    "RestoreResponse",
]
