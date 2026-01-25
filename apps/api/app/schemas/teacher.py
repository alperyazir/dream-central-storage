"""Pydantic schemas for teacher and material metadata payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Teacher Schemas
# =============================================================================


class TeacherBase(BaseModel):
    """Shared attributes required for teacher metadata operations."""

    teacher_id: str = Field(..., max_length=255, description="Unique external teacher ID")
    display_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    status: str = Field(default="active", max_length=20)


class TeacherCreate(TeacherBase):
    """Payload for creating a new teacher record."""

    ai_auto_process_enabled: bool | None = Field(
        default=None, description="Enable auto AI processing (None = use global default)"
    )
    ai_processing_priority: str | None = Field(
        default=None, max_length=20, description="Processing priority (high, normal, low)"
    )
    ai_audio_languages: str | None = Field(
        default=None, max_length=100, description="Comma-separated language codes for audio"
    )


class TeacherUpdate(BaseModel):
    """Payload for updating existing teacher metadata."""

    display_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=20)
    ai_auto_process_enabled: bool | None = Field(default=None)
    ai_processing_priority: str | None = Field(default=None, max_length=20)
    ai_audio_languages: str | None = Field(default=None, max_length=100)


class TeacherRead(TeacherBase):
    """Representation returned by the API for persisted teacher records."""

    id: int
    ai_auto_process_enabled: bool | None = None
    ai_processing_priority: str | None = None
    ai_audio_languages: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeacherWithMaterials(TeacherRead):
    """Teacher with nested list of materials.

    Note: materials field uses Any to avoid circular import with MaterialRead.
    At runtime, this will contain MaterialRead-compatible dictionaries.
    """

    materials: list[Any] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TeacherListItem(TeacherRead):
    """Teacher item in list response with computed fields."""

    material_count: int = Field(default=0, description="Number of materials")
    total_storage_size: int = Field(default=0, description="Total storage size in bytes")


class TeacherListResponse(BaseModel):
    """Paginated teacher list response."""

    items: list[TeacherListItem]
    total: int


# =============================================================================
# Material Schemas
# =============================================================================


class MaterialBase(BaseModel):
    """Shared attributes required for material metadata operations."""

    material_name: str = Field(..., max_length=255, description="Original filename")
    display_name: str | None = Field(default=None, max_length=255)
    file_type: str = Field(..., max_length=50, description="File extension (pdf, txt, docx, etc.)")
    content_type: str = Field(..., max_length=100, description="MIME type")
    size: int = Field(..., ge=0, description="File size in bytes")


class MaterialCreate(MaterialBase):
    """Payload for creating a new material record."""

    teacher_id: int = Field(..., description="Teacher ID this material belongs to")


class MaterialUpdate(BaseModel):
    """Payload for updating existing material metadata."""

    display_name: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=20)


class MaterialRead(MaterialBase):
    """Representation returned by the API for persisted material records."""

    id: int
    status: str
    ai_processing_status: str
    ai_processed_at: datetime | None = None
    ai_job_id: str | None = None
    teacher_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialListItem(MaterialRead):
    """Material item in list response."""

    pass


class MaterialListResponse(BaseModel):
    """Paginated material list response."""

    items: list[MaterialListItem]
    total: int


# =============================================================================
# Storage Stats Schemas
# =============================================================================


class FileTypeStats(BaseModel):
    """Stats for a single file type."""

    count: int = Field(..., description="Number of files")
    size: int = Field(..., description="Total size in bytes")


class StorageStatsResponse(BaseModel):
    """Storage statistics for a teacher."""

    total_size: int = Field(..., description="Total storage size in bytes")
    total_count: int = Field(..., description="Total number of files")
    by_type: dict[str, FileTypeStats] = Field(
        default_factory=dict, description="Breakdown by file type"
    )
    ai_processable_count: int = Field(
        default=0, description="Number of files that can be AI processed"
    )
    ai_processed_count: int = Field(
        default=0, description="Number of files that have been AI processed"
    )
