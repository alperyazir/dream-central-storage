"""Integration tests for book CRUD endpoints."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db import get_db
from app.db.base import Base
from app.main import app
from app.models.book import Book, BookStatusEnum
from app.models.user import User
from app.services import RelocationError, RelocationReport

TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    with TestingSessionLocal() as session:
        yield session


def _create_admin_token() -> dict[str, str]:
    with TestingSessionLocal() as session:
        user = User(email="admin@example.com", hashed_password="hashed")
        session.add(user)
        session.commit()
        session.refresh(user)
        token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module", autouse=True)
def setup_database() -> None:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_tables() -> None:
    with TestingSessionLocal() as session:
        session.query(Book).delete()
        session.query(User).delete()
        session.commit()


def test_create_book_requires_authentication() -> None:
    client = TestClient(app)
    response = client.post(
        "/books",
        json={
            "publisher": "Dream Press",
            "book_name": "Sky Tales",
            "language": "en",
            "category": "fiction",
            "status": "draft",
        },
    )
    assert response.status_code in {401, 403}


def test_create_and_list_books() -> None:
    headers = _create_admin_token()
    client = TestClient(app)

    create_response = client.post(
        "/books",
        json={
            "publisher": "Dream Press",
            "book_name": "Sky Tales",
            "language": "en",
            "category": "fiction",
            "status": "draft",
        },
        headers=headers,
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["book_name"] == "Sky Tales"

    list_response = client.get("/books", headers=headers)
    assert list_response.status_code == 200
    books = list_response.json()
    assert len(books) == 1
    assert books[0]["id"] == created["id"]


def test_get_book_returns_404_when_missing() -> None:
    headers = _create_admin_token()
    client = TestClient(app)

    response = client.get("/books/999", headers=headers)
    assert response.status_code == 404


def test_update_book_modifies_fields() -> None:
    headers = _create_admin_token()
    client = TestClient(app)

    create_response = client.post(
        "/books",
        json={
            "publisher": "Dream Press",
            "book_name": "Sky Tales",
            "language": "en",
            "category": "fiction",
            "status": "draft",
        },
        headers=headers,
    )
    book_id = create_response.json()["id"]

    update_response = client.put(
        f"/books/{book_id}",
        json={"publisher": "Nightfall Publishing", "status": "published"},
        headers=headers,
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["publisher"] == "Nightfall Publishing"
    assert updated["status"] == "published"


def test_invalid_token_is_rejected() -> None:
    headers = {"Authorization": "Bearer invalid.token.string"}
    client = TestClient(app)
    response = client.get("/books", headers=headers)
    assert response.status_code == 401


def test_soft_delete_book_archives_and_moves_assets(monkeypatch) -> None:
    headers = _create_admin_token()
    client = TestClient(app)

    create_response = client.post(
        "/books",
        json={
            "publisher": "DreamPress",
            "book_name": "SkyTales",
            "language": "en",
            "category": "fiction",
            "status": "draft",
        },
        headers=headers,
    )
    book_id = create_response.json()["id"]

    from app.routers import books as books_router

    captured = {}

    def fake_move_prefix_to_trash(**kwargs):
        captured["prefix"] = kwargs["prefix"]
        return RelocationReport(
            source_bucket="books",
            destination_bucket="trash",
            source_prefix=f"DreamPress/SkyTales/",
            destination_prefix="books/DreamPress/SkyTales/",
            objects_moved=2,
        )

    monkeypatch.setattr(books_router, "get_minio_client", lambda settings: MagicMock())
    monkeypatch.setattr(books_router, "move_prefix_to_trash", fake_move_prefix_to_trash)

    response = client.delete(f"/books/{book_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "archived"
    assert captured["prefix"] == "DreamPress/SkyTales/"

    with TestingSessionLocal() as session:
        stored = session.get(Book, book_id)
        assert stored is not None
        assert stored.status == BookStatusEnum.ARCHIVED


def test_soft_delete_book_rolls_back_on_relocation_error(monkeypatch) -> None:
    headers = _create_admin_token()
    client = TestClient(app)

    create_response = client.post(
        "/books",
        json={
            "publisher": "DreamPress",
            "book_name": "SkyTales",
            "language": "en",
            "category": "fiction",
            "status": "draft",
        },
        headers=headers,
    )
    book_id = create_response.json()["id"]

    from app.routers import books as books_router

    monkeypatch.setattr(books_router, "get_minio_client", lambda settings: MagicMock())
    monkeypatch.setattr(
        books_router,
        "move_prefix_to_trash",
        MagicMock(side_effect=RelocationError("boom")),
    )

    response = client.delete(f"/books/{book_id}", headers=headers)
    assert response.status_code == 502

    with TestingSessionLocal() as session:
        stored = session.get(Book, book_id)
        assert stored is not None
        assert stored.status == BookStatusEnum.DRAFT
