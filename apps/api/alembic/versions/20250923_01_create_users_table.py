"""Create users table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20250923_01"
down_revision = "20250922_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=512), nullable=False),
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
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute(
            sa.text(
                """
                CREATE OR REPLACE FUNCTION users_updated_at_timestamp()
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
                CREATE TRIGGER users_updated_at_trigger
                BEFORE UPDATE ON users
                FOR EACH ROW
                EXECUTE FUNCTION users_updated_at_timestamp();
                """
            )
        )
    elif dialect == "sqlite":
        op.execute(
            sa.text(
                """
                CREATE TRIGGER users_updated_at_trigger
                AFTER UPDATE ON users
                FOR EACH ROW
                WHEN NEW.updated_at = OLD.updated_at
                BEGIN
                    UPDATE users
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
        op.execute(sa.text("DROP TRIGGER IF EXISTS users_updated_at_trigger ON users"))
        op.execute(sa.text("DROP FUNCTION IF EXISTS users_updated_at_timestamp()"))
    elif dialect == "sqlite":
        op.execute(sa.text("DROP TRIGGER IF EXISTS users_updated_at_trigger"))

    op.drop_table("users")
