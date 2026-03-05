"""Pydantic schemas for AI-generated content payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ManifestData(BaseModel):
    """Manifest metadata for a single AI content generation."""

    activity_type: str = Field(..., max_length=128)
    title: str = Field(..., max_length=512)
    item_count: int = Field(..., ge=0)
    has_audio: bool = Field(default=False)
    has_passage: bool = Field(default=False)
    difficulty: str | None = Field(default=None, max_length=32)
    language: str = Field(default="en", max_length=64)
    created_by: str | None = Field(default=None, max_length=255)
    created_at: datetime | None = Field(default=None)


class AIContentCreate(BaseModel):
    """Payload for creating a new AI content entry (manifest + content)."""

    manifest: ManifestData
    content: dict


class AIContentCreateResponse(BaseModel):
    """Response after creating AI content."""

    content_id: str
    storage_path: str


class ManifestRead(ManifestData):
    """Manifest returned in list responses, includes content_id."""

    content_id: str


class AIContentRead(BaseModel):
    """Full AI content response (manifest + content)."""

    content_id: str
    manifest: ManifestData
    content: dict


class AudioUploadResponse(BaseModel):
    """Response after uploading a single audio file."""

    filename: str
    storage_path: str
    size: int


class BatchAudioResponse(BaseModel):
    """Response after batch audio upload."""

    uploaded: list[AudioUploadResponse]
    failed: list[str] = Field(default_factory=list)
