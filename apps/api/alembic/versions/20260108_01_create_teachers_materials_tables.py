"""Create teachers and materials tables for teacher content management.

Revision ID: 20260108_01
Revises: 20251230_01
Create Date: 2026-01-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260108_01"
down_revision = "20251230_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create teachers and materials tables."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Step 1: Create teachers table
    op.create_table(
        "teachers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("teacher_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("ai_auto_process_enabled", sa.Boolean(), nullable=True),
        sa.Column("ai_processing_priority", sa.String(length=20), nullable=True),
        sa.Column("ai_audio_languages", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    # Step 2: Create index on teachers.teacher_id for fast lookups
    op.create_index("ix_teachers_teacher_id", "teachers", ["teacher_id"])
    op.create_index("ix_teachers_status", "teachers", ["status"])

    # Step 3: Create updated_at trigger for teachers
    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE OR REPLACE FUNCTION teachers_updated_at_timestamp()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
        )
        op.execute(
            sa.text(
                """
                CREATE TRIGGER teachers_updated_at_trigger
                BEFORE UPDATE ON teachers
                FOR EACH ROW
                EXECUTE FUNCTION teachers_updated_at_timestamp();
                """
            )
        )
    elif dialect == "sqlite":
        op.execute(
            sa.text(
                """
                CREATE TRIGGER teachers_updated_at_trigger
                AFTER UPDATE ON teachers
                FOR EACH ROW
                WHEN NEW.updated_at = OLD.updated_at
                BEGIN
                    UPDATE teachers
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE rowid = NEW.rowid;
                END;
                """
            )
        )

    # Step 4: Create materials table
    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("material_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("ai_processing_status", sa.String(length=30), nullable=False, server_default="not_started"),
        sa.Column("ai_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_job_id", sa.String(length=100), nullable=True),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["teachers.id"],
            name="fk_materials_teacher_id",
            ondelete="CASCADE",
        ),
    )

    # Step 5: Create indexes on materials table
    op.create_index("ix_materials_teacher_id", "materials", ["teacher_id"])
    op.create_index("ix_materials_status", "materials", ["status"])
    op.create_index("ix_materials_ai_processing_status", "materials", ["ai_processing_status"])
    op.create_index("ix_materials_file_type", "materials", ["file_type"])

    # Step 6: Create updated_at trigger for materials
    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE OR REPLACE FUNCTION materials_updated_at_timestamp()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
        )
        op.execute(
            sa.text(
                """
                CREATE TRIGGER materials_updated_at_trigger
                BEFORE UPDATE ON materials
                FOR EACH ROW
                EXECUTE FUNCTION materials_updated_at_timestamp();
                """
            )
        )
    elif dialect == "sqlite":
        op.execute(
            sa.text(
                """
                CREATE TRIGGER materials_updated_at_trigger
                AFTER UPDATE ON materials
                FOR EACH ROW
                WHEN NEW.updated_at = OLD.updated_at
                BEGIN
                    UPDATE materials
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE rowid = NEW.rowid;
                END;
                """
            )
        )


def downgrade() -> None:
    """Drop teachers and materials tables."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Step 1: Drop triggers for materials
    if dialect == "postgresql":
        op.execute(sa.text("DROP TRIGGER IF EXISTS materials_updated_at_trigger ON materials"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS materials_updated_at_timestamp()"))
    elif dialect == "sqlite":
        op.execute(sa.text("DROP TRIGGER IF EXISTS materials_updated_at_trigger"))

    # Step 2: Drop indexes on materials
    op.drop_index("ix_materials_file_type", table_name="materials")
    op.drop_index("ix_materials_ai_processing_status", table_name="materials")
    op.drop_index("ix_materials_status", table_name="materials")
    op.drop_index("ix_materials_teacher_id", table_name="materials")

    # Step 3: Drop materials table
    op.drop_table("materials")

    # Step 4: Drop triggers for teachers
    if dialect == "postgresql":
        op.execute(sa.text("DROP TRIGGER IF EXISTS teachers_updated_at_trigger ON teachers"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS teachers_updated_at_timestamp()"))
    elif dialect == "sqlite":
        op.execute(sa.text("DROP TRIGGER IF EXISTS teachers_updated_at_trigger"))

    # Step 5: Drop indexes on teachers
    op.drop_index("ix_teachers_status", table_name="teachers")
    op.drop_index("ix_teachers_teacher_id", table_name="teachers")

    # Step 6: Drop teachers table
    op.drop_table("teachers")
