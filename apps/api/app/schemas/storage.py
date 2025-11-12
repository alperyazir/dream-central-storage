"""Pydantic schemas for storage-related endpoints."""

from __future__ import annotations

from datetime import datetime
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
    youngest_last_modified: datetime | None = Field(
        default=None,
        description="UTC timestamp for the most recently modified object within this entry",
    )
    eligible_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when the entry exits the enforced retention window",
    )
    eligible_for_deletion: bool = Field(
        default=False,
        description="Indicates whether the entry can be deleted without a retention override",
    )


class RestoreRequest(BaseModel):
    """Request payload for restoring an item from the trash bucket."""

    key: str = Field(..., description="Key identifying the trash entry to restore")


class RestoreResponse(BaseModel):
    """Response returned after initiating a restore operation."""

    restored_key: str
    objects_moved: int
    item_type: Literal["book", "app", "unknown"]
    book: BookRead | None = None


class TrashDeleteRequest(BaseModel):
    """Request payload for permanently deleting a trash entry."""

    key: str = Field(..., description="Key identifying the trash entry to delete")
    force: bool = Field(default=False, description="Bypass retention checks when true")
    override_reason: str | None = Field(
        default=None,
        description="Justification recorded when bypassing retention checks",
        max_length=500,
    )


class TrashDeleteResponse(BaseModel):
    """Response returned after a successful permanent deletion."""

    deleted_key: str
    objects_removed: int
    item_type: Literal["book", "app", "unknown"]


__all__ = [
    "TrashEntryRead",
    "RestoreRequest",
    "RestoreResponse",
    "TrashDeleteRequest",
    "TrashDeleteResponse",
]
