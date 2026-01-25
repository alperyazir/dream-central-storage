"""ORM model for teacher metadata."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.material import Material


class TeacherStatusEnum(str, enum.Enum):
    """Lifecycle states for teacher records."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Teacher(Base):
    """Represents a teacher entity persisted in PostgreSQL."""

    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teacher_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # AI Processing Settings (nullable = use global default)
    ai_auto_process_enabled: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=None
    )
    ai_processing_priority: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=None
    )
    ai_audio_languages: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None
    )

    # Relationship to materials (cascade delete: when teacher is deleted, all materials are deleted too)
    materials: Mapped[list["Material"]] = relationship(
        "Material", back_populates="teacher_rel", cascade="all, delete-orphan"
    )
