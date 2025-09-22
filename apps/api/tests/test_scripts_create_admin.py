"""Tests for the admin bootstrap script."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import verify_password
from app.db.base import Base
from app.models.user import User
from app.scripts.create_admin import create_admin_user


@pytest.fixture()
def session_local() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_create_admin_user_hashes_password(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        user = create_admin_user(session, email="admin@example.com", password="secret")
        session.refresh(user)
        assert user.email == "admin@example.com"
        assert user.hashed_password != "secret"
        assert verify_password("secret", user.hashed_password)


def test_create_admin_user_rejects_duplicates(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        create_admin_user(session, email="admin@example.com", password="secret")
        session.commit()

    with session_local() as session:
        create_admin_user(session, email="other@example.com", password="secret")
        session.commit()

    with session_local() as session:
        with pytest.raises(ValueError):
            create_admin_user(session, email="admin@example.com", password="secret")
