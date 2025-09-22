"""Shared repository helpers used by concrete persistence classes."""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Small abstraction around SQLAlchemy session interactions."""

    def __init__(self, model: type[T]):
        self._model = model

    @property
    def model(self) -> type[T]:
        """Return the SQLAlchemy model handled by the repository."""

        return self._model

    def add(self, session: Session, instance: T) -> T:
        """Persist a new instance and refresh it with database defaults."""

        session.add(instance)
        session.flush()
        session.refresh(instance)
        return instance

    def get(self, session: Session, identifier: int) -> T | None:
        """Fetch a single instance by primary key."""

        return session.get(self._model, identifier)

    def list_all(self, session: Session) -> list[T]:
        """Return all instances of the model."""

        result = session.execute(select(self._model))
        return list(result.scalars())
