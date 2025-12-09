"""Make book category field optional"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251116_01"
down_revision = "20251115_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make category column nullable
    op.alter_column("books", "category", existing_type=sa.String(length=128), nullable=True)


def downgrade() -> None:
    # Revert category column to non-nullable
    # First set empty strings for any NULL values to avoid constraint violations
    op.execute("UPDATE books SET category = '' WHERE category IS NULL")
    op.alter_column("books", "category", existing_type=sa.String(length=128), nullable=False)
