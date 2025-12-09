"""Database access helpers for webhook subscriptions and delivery logs."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.webhook import WebhookDeliveryLog, WebhookSubscription
from app.repositories.base import BaseRepository


class WebhookSubscriptionRepository(BaseRepository[WebhookSubscription]):
    """Repository for interacting with webhook subscription records."""

    def __init__(self) -> None:
        super().__init__(model=WebhookSubscription)

    def create(self, session: Session, *, data: dict[str, object]) -> WebhookSubscription:
        """Create a new webhook subscription."""
        subscription = WebhookSubscription(**data)
        created = self.add(session, subscription)
        session.commit()
        return created

    def list_all(self, session: Session) -> list[WebhookSubscription]:
        """Return all webhook subscriptions."""
        return super().list_all(session)

    def list_active(self, session: Session) -> list[WebhookSubscription]:
        """Return only active webhook subscriptions."""
        statement = select(WebhookSubscription).where(WebhookSubscription.is_active == True)  # noqa: E712
        result = session.execute(statement)
        return list(result.scalars())

    def get_by_id(self, session: Session, identifier: int) -> WebhookSubscription | None:
        """Get webhook subscription by ID."""
        return self.get(session, identifier)

    def update(
        self, session: Session, subscription: WebhookSubscription, *, data: dict[str, object]
    ) -> WebhookSubscription:
        """Update an existing webhook subscription."""
        for field, value in data.items():
            if value is not None:  # Only update non-null values
                setattr(subscription, field, value)
        session.flush()
        session.refresh(subscription)
        session.commit()
        return subscription

    def delete(self, session: Session, subscription: WebhookSubscription) -> None:
        """Permanently delete a webhook subscription."""
        session.delete(subscription)
        session.commit()


class WebhookDeliveryLogRepository(BaseRepository[WebhookDeliveryLog]):
    """Repository for interacting with webhook delivery log records."""

    def __init__(self) -> None:
        super().__init__(model=WebhookDeliveryLog)

    def create(self, session: Session, *, data: dict[str, object]) -> WebhookDeliveryLog:
        """Create a new webhook delivery log entry."""
        log = WebhookDeliveryLog(**data)
        created = self.add(session, log)
        session.commit()
        return created

    def get_by_id(self, session: Session, identifier: int) -> WebhookDeliveryLog | None:
        """Get webhook delivery log by ID."""
        return self.get(session, identifier)

    def list_by_subscription(
        self, session: Session, subscription_id: int, limit: int = 100
    ) -> list[WebhookDeliveryLog]:
        """Get delivery logs for a specific subscription."""
        statement = (
            select(WebhookDeliveryLog)
            .where(WebhookDeliveryLog.subscription_id == subscription_id)
            .order_by(WebhookDeliveryLog.created_at.desc())
            .limit(limit)
        )
        result = session.execute(statement)
        return list(result.scalars())

    def update(
        self, session: Session, log: WebhookDeliveryLog, *, data: dict[str, object]
    ) -> WebhookDeliveryLog:
        """Update an existing webhook delivery log."""
        for field, value in data.items():
            setattr(log, field, value)
        session.flush()
        session.refresh(log)
        session.commit()
        return log
