"""Create publishers table and normalize schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251214_01"
down_revision = "20251116_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Create publishers table
    op.create_table(
        "publishers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(length=512), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
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

    # Step 2: Create index on publishers.name for fast lookups
    op.create_index("ix_publishers_name", "publishers", ["name"])

    # Step 3: Create updated_at trigger for publishers (PostgreSQL)
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE OR REPLACE FUNCTION publishers_updated_at_timestamp()
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
                CREATE TRIGGER publishers_updated_at_trigger
                BEFORE UPDATE ON publishers
                FOR EACH ROW
                EXECUTE FUNCTION publishers_updated_at_timestamp();
                """
            )
        )
    elif dialect == "sqlite":
        op.execute(
            sa.text(
                """
                CREATE TRIGGER publishers_updated_at_trigger
                AFTER UPDATE ON publishers
                FOR EACH ROW
                WHEN NEW.updated_at = OLD.updated_at
                BEGIN
                    UPDATE publishers
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE rowid = NEW.rowid;
                END;
                """
            )
        )

    # Step 4: Extract unique publishers from books and insert into publishers table
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT DISTINCT publisher FROM books WHERE publisher IS NOT NULL AND publisher != ''")
    )
    publishers = [row[0] for row in result]

    for pub_name in publishers:
        connection.execute(
            sa.text("INSERT INTO publishers (name, display_name) VALUES (:name, :name)"),
            {"name": pub_name}
        )

    # Step 5: Add publisher_id column to books table
    op.add_column("books", sa.Column("publisher_id", sa.Integer(), nullable=True))

    # Step 6: Update books.publisher_id to reference publishers.id
    connection.execute(
        sa.text(
            """
            UPDATE books SET publisher_id = (
                SELECT id FROM publishers WHERE publishers.name = books.publisher
            )
            """
        )
    )

    # Step 7: Create foreign key constraint
    op.create_foreign_key(
        "fk_books_publisher_id",
        "books", "publishers",
        ["publisher_id"], ["id"]
    )

    # Step 8: Create index on books.publisher_id for query performance
    op.create_index("ix_books_publisher_id", "books", ["publisher_id"])


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Step 1: Drop index on books.publisher_id
    op.drop_index("ix_books_publisher_id", table_name="books")

    # Step 2: Drop foreign key constraint
    op.drop_constraint("fk_books_publisher_id", "books", type_="foreignkey")

    # Step 3: Drop publisher_id column from books
    op.drop_column("books", "publisher_id")

    # Step 4: Drop updated_at trigger for publishers
    if dialect == "postgresql":
        op.execute(sa.text("DROP TRIGGER IF EXISTS publishers_updated_at_trigger ON publishers"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS publishers_updated_at_timestamp()"))
    elif dialect == "sqlite":
        op.execute(sa.text("DROP TRIGGER IF EXISTS publishers_updated_at_trigger"))

    # Step 5: Drop index on publishers.name
    op.drop_index("ix_publishers_name", table_name="publishers")

    # Step 6: Drop publishers table
    op.drop_table("publishers")
