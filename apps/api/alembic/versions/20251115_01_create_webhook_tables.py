"""Create webhook_subscriptions and webhook_delivery_logs tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251115_01"
down_revision = "20250113_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create webhook_subscriptions table
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("secret", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("event_types", sa.String(length=255), nullable=True),
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

    # Create webhook_delivery_logs table
    op.create_table(
        "webhook_delivery_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum("book.created", "book.updated", "book.deleted", name="webhook_event_type", native_enum=False),
            nullable=False,
        ),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "success", "failed", name="webhook_delivery_status", native_enum=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for efficient queries
    op.create_index("ix_webhook_delivery_logs_subscription_id", "webhook_delivery_logs", ["subscription_id"])
    op.create_index("ix_webhook_delivery_logs_status", "webhook_delivery_logs", ["status"])
    op.create_index("ix_webhook_delivery_logs_created_at", "webhook_delivery_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_webhook_delivery_logs_created_at", "webhook_delivery_logs")
    op.drop_index("ix_webhook_delivery_logs_status", "webhook_delivery_logs")
    op.drop_index("ix_webhook_delivery_logs_subscription_id", "webhook_delivery_logs")
    op.drop_table("webhook_delivery_logs")
    op.drop_table("webhook_subscriptions")
    op.execute("DROP TYPE IF EXISTS webhook_event_type")
    op.execute("DROP TYPE IF EXISTS webhook_delivery_status")
