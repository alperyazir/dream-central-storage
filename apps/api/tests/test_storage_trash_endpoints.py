"""Tests for storage trash listing and restore endpoints."""

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
from app.services import RelocationReport, RestorationError, TrashEntry

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


def _create_admin_headers() -> dict[str, str]:
    with TestingSessionLocal() as session:
        user = User(email="admin@example.com", hashed_password="hashed")
        session.add(user)
        session.commit()
        session.refresh(user)
        token = create_access_token(subject=str(user.id), expires_delta=timedelta(hours=1))
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


def test_list_trash_requires_authentication() -> None:
    client = TestClient(app)
    response = client.get("/storage/trash")
    assert response.status_code in {401, 403}


def test_list_trash_returns_entries(monkeypatch) -> None:
    from app.routers import storage as storage_router

    client = TestClient(app)
    headers = _create_admin_headers()

    monkeypatch.setattr(storage_router, "get_minio_client", lambda settings: MagicMock())
    monkeypatch.setattr(
        storage_router,
        "list_trash_entries",
        lambda client, bucket, retention: [
            TrashEntry(
                key="books/Press/Atlas/",
                bucket="books",
                path="Press/Atlas",
                item_type="book",
                object_count=2,
                total_size=15,
                metadata={"publisher": "Press", "book_name": "Atlas"},
            )
        ],
    )

    response = client.get("/storage/trash", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "key": "books/Press/Atlas/",
            "bucket": "books",
            "path": "Press/Atlas",
            "item_type": "book",
            "object_count": 2,
            "total_size": 15,
            "metadata": {"publisher": "Press", "book_name": "Atlas"},
            "youngest_last_modified": None,
            "eligible_at": None,
            "eligible_for_deletion": False,
        }
    ]


def test_restore_book_success(monkeypatch) -> None:
    from app.routers import storage as storage_router

    with TestingSessionLocal() as session:
        book = Book(
            publisher="Press",
            book_name="Atlas",
            language="en",
            category="fiction",
            status=BookStatusEnum.ARCHIVED,
        )
        session.add(book)
        session.commit()

    headers = _create_admin_headers()
    client = TestClient(app)

    monkeypatch.setattr(storage_router, "get_minio_client", lambda settings: MagicMock())
    monkeypatch.setattr(
        storage_router,
        "restore_prefix_from_trash",
        lambda **kwargs: RelocationReport(
            source_bucket="trash",
            destination_bucket="books",
            source_prefix="books/Press/Atlas/",
            destination_prefix="Press/Atlas/",
            objects_moved=3,
        ),
    )

    response = client.post(
        "/storage/restore",
        json={"key": "books/Press/Atlas/"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["objects_moved"] == 3
    assert body["item_type"] == "book"
    assert body["book"]["book_name"] == "Atlas"
    assert body["book"]["status"] == "published"

    with TestingSessionLocal() as session:
        stored = session.query(Book).filter(Book.book_name == "Atlas").one()
        assert stored.status == BookStatusEnum.PUBLISHED


def test_restore_book_missing_trash(monkeypatch) -> None:
    from app.routers import storage as storage_router

    with TestingSessionLocal() as session:
        book = Book(
            publisher="Press",
            book_name="Atlas",
            language="en",
            category="fiction",
            status=BookStatusEnum.ARCHIVED,
        )
        session.add(book)
        session.commit()

    headers = _create_admin_headers()
    client = TestClient(app)

    monkeypatch.setattr(storage_router, "get_minio_client", lambda settings: MagicMock())
    monkeypatch.setattr(
        storage_router,
        "restore_prefix_from_trash",
        lambda **kwargs: (_ for _ in ()).throw(
            RestorationError("No trash objects found for key 'books/Press/Atlas/'")
        ),
    )

    response = client.post(
        "/storage/restore",
        json={"key": "books/Press/Atlas/"},
        headers=headers,
    )

    assert response.status_code == 404


def test_restore_book_conflict_when_not_archived(monkeypatch) -> None:
    from app.routers import storage as storage_router

    with TestingSessionLocal() as session:
        book = Book(
            publisher="Press",
            book_name="Atlas",
            language="en",
            category="fiction",
            status=BookStatusEnum.PUBLISHED,
        )
        session.add(book)
        session.commit()

    headers = _create_admin_headers()
    client = TestClient(app)

    monkeypatch.setattr(storage_router, "get_minio_client", lambda settings: MagicMock())
    monkeypatch.setattr(
        storage_router,
        "restore_prefix_from_trash",
        lambda **kwargs: RelocationReport(
            source_bucket="trash",
            destination_bucket="books",
            source_prefix="books/Press/Atlas/",
            destination_prefix="Press/Atlas/",
            objects_moved=1,
        ),
    )

    response = client.post(
        "/storage/restore",
        json={"key": "books/Press/Atlas/"},
        headers=headers,
    )

    assert response.status_code == 409


def test_restore_requires_authentication(monkeypatch) -> None:
    from app.routers import storage as storage_router

    monkeypatch.setattr(storage_router, "get_minio_client", lambda settings: MagicMock())

    client = TestClient(app)
    response = client.post("/storage/restore", json={"key": "books/Press/Atlas/"})
    assert response.status_code in {401, 403}
