"""Add book_title, book_cover, and activity_count fields to books table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251116_03"
down_revision = "20251116_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.add_column("books", sa.Column("book_title", sa.String(length=255), nullable=True))
    op.add_column("books", sa.Column("book_cover", sa.String(length=512), nullable=True))
    op.add_column("books", sa.Column("activity_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    # Drop columns
    op.drop_column("books", "activity_count")
    op.drop_column("books", "book_cover")
    op.drop_column("books", "book_title")
