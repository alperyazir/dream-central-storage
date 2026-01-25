"""ORM model for teacher material metadata."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.teacher import Teacher


class MaterialStatusEnum(str, enum.Enum):
    """Lifecycle states for material records."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class AIProcessingStatusEnum(str, enum.Enum):
    """AI processing status for materials."""

    NOT_STARTED = "not_started"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"  # For non-text materials (images, audio, video)


# Text-based file types that support AI processing
TEXT_MATERIAL_TYPES = frozenset({"pdf", "txt", "docx", "doc"})


class Material(Base):
    """Represents a teacher material metadata record persisted in PostgreSQL."""

    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, txt, docx, mp3, etc.
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)  # MIME type
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )

    # AI Processing tracking
    ai_processing_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="not_started", server_default="not_started"
    )
    ai_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ai_job_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Foreign key to teachers table
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)

    # Relationship to Teacher model
    teacher_rel: Mapped["Teacher"] = relationship("Teacher", back_populates="materials")

    @property
    def is_text_material(self) -> bool:
        """Check if material supports AI processing."""
        return self.file_type.lower() in TEXT_MATERIAL_TYPES

    @property
    def storage_path(self) -> str:
        """Get MinIO storage path for this material."""
        return f"{self.teacher_rel.teacher_id}/materials/{self.material_name}"

    @property
    def ai_data_path(self) -> str:
        """Get MinIO path for AI-generated data."""
        return f"{self.teacher_rel.teacher_id}/materials/{self.material_name}/ai-data"
