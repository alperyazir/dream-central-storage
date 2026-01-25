"""Add AI processing settings columns to publishers table.

Revision ID: 20251230_01
Revises: 20251221_01
Create Date: 2024-12-30
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251230_01"
down_revision = "20251221_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add AI processing settings columns to publishers table."""
    op.add_column(
        "publishers",
        sa.Column("ai_auto_process_enabled", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "publishers",
        sa.Column("ai_processing_priority", sa.String(20), nullable=True),
    )
    op.add_column(
        "publishers",
        sa.Column("ai_audio_languages", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    """Remove AI processing settings columns from publishers table."""
    op.drop_column("publishers", "ai_audio_languages")
    op.drop_column("publishers", "ai_processing_priority")
    op.drop_column("publishers", "ai_auto_process_enabled")
