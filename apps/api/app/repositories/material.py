"""Database access helpers for material entities."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.material import (
    AIProcessingStatusEnum,
    Material,
    TEXT_MATERIAL_TYPES,
)
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class MaterialRepository(BaseRepository[Material]):
    """Repository for interacting with material records."""

    def __init__(self) -> None:
        super().__init__(model=Material)

    def list_by_teacher(
        self,
        session: Session,
        teacher_id: int,
        status: str | None = None,
        file_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Material]:
        """Return materials for a specific teacher with optional filters."""
        statement = select(Material).where(Material.teacher_id == teacher_id)

        if status:
            statement = statement.where(Material.status == status)

        if file_type:
            statement = statement.where(Material.file_type == file_type)

        statement = statement.order_by(Material.created_at.desc())
        statement = statement.offset(skip).limit(limit)
        return list(session.scalars(statement).all())

    def count_by_teacher(
        self,
        session: Session,
        teacher_id: int,
        status: str | None = None,
    ) -> int:
        """Count materials for a specific teacher."""
        statement = (
            select(func.count())
            .select_from(Material)
            .where(Material.teacher_id == teacher_id)
        )
        if status:
            statement = statement.where(Material.status == status)
        return session.execute(statement).scalar() or 0

    def get_by_teacher_and_name(
        self,
        session: Session,
        teacher_id: int,
        material_name: str,
    ) -> Material | None:
        """Fetch a material by teacher ID and material name."""
        statement = select(Material).where(
            Material.teacher_id == teacher_id, Material.material_name == material_name
        )
        return session.scalars(statement).first()

    def get_storage_stats(
        self,
        session: Session,
        teacher_id: int,
    ) -> dict:
        """Get storage statistics for a teacher.

        Returns:
            Dict with total_size, total_count, by_type breakdown, and AI stats.
        """
        # Total size and count
        total_stmt = select(
            func.count().label("count"),
            func.coalesce(func.sum(Material.size), 0).label("size"),
        ).where(
            Material.teacher_id == teacher_id, Material.status != "archived"
        )
        total_result = session.execute(total_stmt).first()
        total_count = total_result.count if total_result else 0
        total_size = total_result.size if total_result else 0

        # Breakdown by file type
        by_type_stmt = (
            select(
                Material.file_type,
                func.count().label("count"),
                func.coalesce(func.sum(Material.size), 0).label("size"),
            )
            .where(Material.teacher_id == teacher_id, Material.status != "archived")
            .group_by(Material.file_type)
        )
        by_type_result = session.execute(by_type_stmt).all()
        by_type = {
            row.file_type: {"count": row.count, "size": row.size}
            for row in by_type_result
        }

        # AI processable count (text materials)
        ai_processable_stmt = (
            select(func.count())
            .select_from(Material)
            .where(
                Material.teacher_id == teacher_id,
                Material.status != "archived",
                Material.file_type.in_(TEXT_MATERIAL_TYPES),
            )
        )
        ai_processable_count = session.execute(ai_processable_stmt).scalar() or 0

        # AI processed count
        ai_processed_stmt = (
            select(func.count())
            .select_from(Material)
            .where(
                Material.teacher_id == teacher_id,
                Material.status != "archived",
                Material.ai_processing_status == AIProcessingStatusEnum.COMPLETED.value,
            )
        )
        ai_processed_count = session.execute(ai_processed_stmt).scalar() or 0

        return {
            "total_size": int(total_size),
            "total_count": total_count,
            "by_type": by_type,
            "ai_processable_count": ai_processable_count,
            "ai_processed_count": ai_processed_count,
        }

    def list_pending_ai_processing(
        self,
        session: Session,
        teacher_id: int | None = None,
        limit: int = 100,
    ) -> list[Material]:
        """List materials that need AI processing."""
        statement = select(Material).where(
            Material.status != "archived",
            Material.file_type.in_(TEXT_MATERIAL_TYPES),
            Material.ai_processing_status.in_(
                [
                    AIProcessingStatusEnum.NOT_STARTED.value,
                    AIProcessingStatusEnum.FAILED.value,
                ]
            ),
        )

        if teacher_id is not None:
            statement = statement.where(Material.teacher_id == teacher_id)

        statement = statement.order_by(Material.created_at).limit(limit)
        return list(session.scalars(statement).all())

    def list_processing(
        self,
        session: Session,
        teacher_id: int | None = None,
    ) -> list[Material]:
        """List materials currently being processed."""
        statement = select(Material).where(
            Material.ai_processing_status.in_(
                [
                    AIProcessingStatusEnum.QUEUED.value,
                    AIProcessingStatusEnum.PROCESSING.value,
                ]
            )
        )

        if teacher_id is not None:
            statement = statement.where(Material.teacher_id == teacher_id)

        return list(session.scalars(statement).all())

    def create(self, session: Session, *, data: dict[str, object]) -> Material:
        """Create a new material record."""
        # Set AI processing status based on file type
        file_type = str(data.get("file_type", "")).lower()
        if file_type not in TEXT_MATERIAL_TYPES:
            data["ai_processing_status"] = AIProcessingStatusEnum.NOT_APPLICABLE.value

        material = Material(**data)
        created = self.add(session, material)
        session.commit()
        return created

    def update(
        self, session: Session, material: Material, *, data: dict[str, object]
    ) -> Material:
        """Update an existing material."""
        for field, value in data.items():
            setattr(material, field, value)
        session.flush()
        session.refresh(material)
        session.commit()
        return material

    def update_ai_status(
        self,
        session: Session,
        material: Material,
        status: str,
        job_id: str | None = None,
    ) -> Material:
        """Update AI processing status for a material."""
        material.ai_processing_status = status
        if job_id is not None:
            material.ai_job_id = job_id
        if status == AIProcessingStatusEnum.COMPLETED.value:
            material.ai_processed_at = datetime.now(timezone.utc)
        session.flush()
        session.refresh(material)
        session.commit()
        return material

    def delete(self, session: Session, material: Material) -> None:
        """Permanently remove a material record from the database."""
        logger.info(
            f"Deleting material '{material.material_name}' "
            f"(ID: {material.id}, Teacher ID: {material.teacher_id})"
        )
        session.delete(material)
        session.commit()
        logger.info(f"Successfully deleted material '{material.material_name}'")

    def soft_delete(self, session: Session, material: Material) -> Material:
        """Soft-delete a material by setting status to archived."""
        material.status = "archived"
        session.flush()
        session.refresh(material)
        session.commit()
        return material
