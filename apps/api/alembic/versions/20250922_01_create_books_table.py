"""Create books table"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20250922_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("publisher", sa.String(length=255), nullable=False),
        sa.Column("book_name", sa.String(length=255), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.Enum("draft", "published", "archived", name="book_status", native_enum=False),
            nullable=False,
            server_default="draft",
        ),
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

    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE OR REPLACE FUNCTION books_updated_at_timestamp()
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
                CREATE TRIGGER books_updated_at_trigger
                BEFORE UPDATE ON books
                FOR EACH ROW
                EXECUTE FUNCTION books_updated_at_timestamp();
                """
            )
        )
    elif dialect == "sqlite":
        op.execute(
            sa.text(
                """
                CREATE TRIGGER books_updated_at_trigger
                AFTER UPDATE ON books
                FOR EACH ROW
                WHEN NEW.updated_at = OLD.updated_at
                BEGIN
                    UPDATE books
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE rowid = NEW.rowid;
                END;
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(sa.text("DROP TRIGGER IF EXISTS books_updated_at_trigger ON books"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS books_updated_at_timestamp()"))
    elif dialect == "sqlite":
        op.execute(sa.text("DROP TRIGGER IF EXISTS books_updated_at_trigger"))

    op.drop_table("books")
