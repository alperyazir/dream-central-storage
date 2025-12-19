"""Drop publisher column and make publisher_id required"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251214_02"
down_revision = "20251214_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Ensure all books have a publisher_id (handle any NULL values)
    # Create a default publisher for orphan books if needed
    connection = op.get_bind()

    # Check for books with NULL publisher_id
    result = connection.execute(
        sa.text("SELECT COUNT(*) FROM books WHERE publisher_id IS NULL")
    )
    null_count = result.scalar()

    if null_count > 0:
        # Create or get default publisher for orphans
        connection.execute(
            sa.text("""
                INSERT INTO publishers (name, display_name, status)
                VALUES ('_unknown', 'Unknown Publisher', 'inactive')
                ON CONFLICT (name) DO NOTHING
            """)
        )
        # Get the default publisher's id
        result = connection.execute(
            sa.text("SELECT id FROM publishers WHERE name = '_unknown'")
        )
        default_publisher_id = result.scalar()

        # Update orphan books
        connection.execute(
            sa.text("UPDATE books SET publisher_id = :pid WHERE publisher_id IS NULL"),
            {"pid": default_publisher_id}
        )

    # Step 2: Make publisher_id NOT NULL
    op.alter_column(
        "books",
        "publisher_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Step 3: Drop the publisher string column
    op.drop_column("books", "publisher")


def downgrade() -> None:
    # Step 1: Re-add the publisher string column
    op.add_column(
        "books",
        sa.Column("publisher", sa.String(length=255), nullable=True)
    )

    # Step 2: Populate publisher from the relationship
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            UPDATE books SET publisher = (
                SELECT name FROM publishers WHERE publishers.id = books.publisher_id
            )
        """)
    )

    # Step 3: Make publisher NOT NULL (restore original constraint)
    op.alter_column(
        "books",
        "publisher",
        existing_type=sa.String(length=255),
        nullable=False,
    )

    # Step 4: Make publisher_id nullable again
    op.alter_column(
        "books",
        "publisher_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
