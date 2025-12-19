"""Database access helpers for publisher entities."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.publisher import Publisher
from app.repositories.base import BaseRepository


class PublisherRepository(BaseRepository[Publisher]):
    """Repository for interacting with publisher records."""

    def __init__(self) -> None:
        super().__init__(model=Publisher)

    def list_all(self, session: Session) -> list[Publisher]:
        """Return all publishers."""
        statement = select(Publisher)
        return list(session.scalars(statement).all())

    def list_paginated(self, session: Session, skip: int = 0, limit: int = 100) -> list[Publisher]:
        """Return publishers with pagination."""
        statement = select(Publisher).offset(skip).limit(limit)
        return list(session.scalars(statement).all())

    def get_by_name(self, session: Session, name: str) -> Publisher | None:
        """Fetch a publisher by unique name."""
        statement = select(Publisher).where(Publisher.name == name)
        result = session.execute(statement)
        return result.scalars().first()

    def get_or_create_by_name(self, session: Session, name: str) -> Publisher:
        """Get existing publisher by name or create a new one."""
        publisher = self.get_by_name(session, name)
        if publisher is not None:
            return publisher

        # Create new publisher with name as display_name
        publisher = Publisher(name=name, display_name=name)
        return self.add(session, publisher)

    def get_with_books(self, session: Session, publisher_id: int) -> Publisher | None:
        """Fetch a publisher with books eager-loaded to avoid N+1 queries."""
        statement = (
            select(Publisher)
            .options(selectinload(Publisher.books))
            .where(Publisher.id == publisher_id)
        )
        return session.scalars(statement).first()

    def create(self, session: Session, *, data: dict[str, object]) -> Publisher:
        """Create a new publisher record."""
        publisher = Publisher(**data)
        created = self.add(session, publisher)
        session.commit()
        return created

    def update(self, session: Session, publisher: Publisher, *, data: dict[str, object]) -> Publisher:
        """Update an existing publisher."""
        for field, value in data.items():
            setattr(publisher, field, value)
        session.flush()
        session.refresh(publisher)
        session.commit()
        return publisher

    def delete(self, session: Session, publisher: Publisher) -> None:
        """Permanently remove a publisher record from the database."""
        session.delete(publisher)
        session.commit()
