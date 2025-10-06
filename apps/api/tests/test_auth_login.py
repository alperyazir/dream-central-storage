"""Tests for the authentication login endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, create_password_hash
from app.db import get_db
from app.db.base import Base
from app.main import app
from app.models.user import User


def _setup_in_memory_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_login_returns_token_for_valid_credentials() -> None:
    test_session_local = _setup_in_memory_db()

    def override_get_db():
        with test_session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with test_session_local() as session:
        user = User(
            email="admin@example.com",
            hashed_password=create_password_hash("super-secret"),
        )
        session.add(user)
        session.commit()

    client = TestClient(app)
    response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "super-secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]

    app.dependency_overrides.pop(get_db, None)


def test_login_rejects_invalid_credentials() -> None:
    test_session_local = _setup_in_memory_db()

    def override_get_db():
        with test_session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with test_session_local() as session:
        user = User(
            email="admin@example.com",
            hashed_password=create_password_hash("super-secret"),
        )
        session.add(user)
        session.commit()

    client = TestClient(app)
    response = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "incorrect"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"

    app.dependency_overrides.pop(get_db, None)


def test_session_endpoint_validates_token() -> None:
    test_session_local = _setup_in_memory_db()

    def override_get_db():
        with test_session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with test_session_local() as session:
        user = User(
            email="admin@example.com",
            hashed_password=create_password_hash("super-secret"),
        )
        session.add(user)
        session.commit()

        token = create_access_token(subject=str(user.id))

    client = TestClient(app)
    response = client.get(
        "/auth/session",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == 1
    assert body["email"] == "admin@example.com"
    assert body["token_type"] == "bearer"

    app.dependency_overrides.pop(get_db, None)


def test_session_endpoint_rejects_invalid_token() -> None:
    app.dependency_overrides[get_db] = lambda: (yield MagicMock())

    client = TestClient(app)
    response = client.get(
        "/auth/session",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"

    app.dependency_overrides.pop(get_db, None)
