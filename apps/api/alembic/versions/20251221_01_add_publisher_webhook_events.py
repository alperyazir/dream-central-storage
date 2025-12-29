"""Add publisher webhook event types"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251221_01"
down_revision = "20251214_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The webhook_event_type column uses native_enum=False, which means it stores
    # as VARCHAR with a CHECK constraint. We need to update the CHECK constraint
    # to include the new publisher event types.

    connection = op.get_bind()

    # First, drop any existing check constraint on event_type
    result = connection.execute(sa.text("""
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'webhook_delivery_logs'::regclass
        AND contype = 'c'
        AND pg_get_constraintdef(oid) LIKE '%event_type%'
    """))
    constraint_names = [row[0] for row in result]

    for constraint_name in constraint_names:
        op.drop_constraint(constraint_name, "webhook_delivery_logs", type_="check")

    # Fix existing data: convert uppercase enum NAMES to lowercase VALUES
    # This handles data that may have been stored incorrectly
    connection.execute(sa.text("""
        UPDATE webhook_delivery_logs SET event_type = 'book.created' WHERE event_type = 'BOOK_CREATED';
    """))
    connection.execute(sa.text("""
        UPDATE webhook_delivery_logs SET event_type = 'book.updated' WHERE event_type = 'BOOK_UPDATED';
    """))
    connection.execute(sa.text("""
        UPDATE webhook_delivery_logs SET event_type = 'book.deleted' WHERE event_type = 'BOOK_DELETED';
    """))

    # Add new CHECK constraint with all event types
    op.create_check_constraint(
        "ck_webhook_delivery_logs_event_type",
        "webhook_delivery_logs",
        "event_type IN ('book.created', 'book.updated', 'book.deleted', 'publisher.created', 'publisher.updated', 'publisher.deleted')"
    )


def downgrade() -> None:
    # Drop the new constraint
    op.drop_constraint("ck_webhook_delivery_logs_event_type", "webhook_delivery_logs", type_="check")

    # Restore original constraint (only book events)
    # First delete any publisher events that may have been logged
    connection = op.get_bind()
    connection.execute(sa.text("""
        DELETE FROM webhook_delivery_logs
        WHERE event_type IN ('publisher.created', 'publisher.updated', 'publisher.deleted')
    """))

    op.create_check_constraint(
        "ck_webhook_delivery_logs_event_type",
        "webhook_delivery_logs",
        "event_type IN ('book.created', 'book.updated', 'book.deleted')"
    )
