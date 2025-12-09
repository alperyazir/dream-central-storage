"""Remove version field from books table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251116_02"
down_revision = "20251116_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop version column
    op.drop_column("books", "version")


def downgrade() -> None:
    # Re-add version column
    op.add_column("books", sa.Column("version", sa.String(length=64), nullable=True))
