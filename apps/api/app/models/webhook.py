"""ORM models for webhook subscriptions and delivery logs."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebhookEventType(str, enum.Enum):
    """Supported webhook event types."""

    BOOK_CREATED = "book.created"
    BOOK_UPDATED = "book.updated"
    BOOK_DELETED = "book.deleted"
    PUBLISHER_CREATED = "publisher.created"
    PUBLISHER_UPDATED = "publisher.updated"
    PUBLISHER_DELETED = "publisher.deleted"


class WebhookDeliveryStatus(str, enum.Enum):
    """Delivery status for webhook events."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class WebhookSubscription(Base):
    """Represents a webhook subscription for receiving events."""

    __tablename__ = "webhook_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # Event type filters (comma-separated list, e.g., "book.created,book.updated")
    # If empty/null, all events are sent
    event_types: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class WebhookDeliveryLog(Base):
    """Logs webhook delivery attempts for debugging and monitoring."""

    __tablename__ = "webhook_delivery_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(50),  # Store as string to avoid enum name/value confusion
        nullable=False,
    )
    payload: Mapped[str] = mapped_column(Text, nullable=False)  # JSON payload as text
    status: Mapped[str] = mapped_column(
        String(20),  # Store as string to avoid enum name/value confusion
        nullable=False,
        default="pending",
    )
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
