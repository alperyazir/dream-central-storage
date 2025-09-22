"""Repository utilities for user persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Data-access helper for administrator accounts."""

    def __init__(self) -> None:
        super().__init__(model=User)

    def get_by_email(self, session: Session, email: str) -> User | None:
        """Return a user matching the supplied email if it exists."""

        statement = select(self.model).where(self.model.email == email)
        result = session.execute(statement)
        return result.scalars().one_or_none()
