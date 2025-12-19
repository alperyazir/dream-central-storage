"""Pydantic schemas for publisher asset management."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AssetTypeInfo(BaseModel):
    """Information about an asset type folder."""

    name: str
    file_count: int
    total_size: int


class PublisherAssetsResponse(BaseModel):
    """Response for listing all asset types for a publisher."""

    publisher_id: int
    publisher_name: str
    asset_types: list[AssetTypeInfo]


class AssetFileInfo(BaseModel):
    """Information about a single file in an asset type."""

    name: str
    path: str
    size: int
    content_type: str
    last_modified: datetime | None = None
