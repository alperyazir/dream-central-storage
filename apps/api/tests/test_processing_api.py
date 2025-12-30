"""Integration tests for AI processing API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

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
from app.models.publisher import Publisher
from app.models.user import User
from app.services.queue.models import (
    JobAlreadyExistsError,
    JobPriority,
    ProcessingJob,
    ProcessingJobType,
    ProcessingStatus,
)

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


def _create_publisher_and_book() -> tuple[int, int]:
    """Create a test publisher and book, return (publisher_id, book_id)."""
    with TestingSessionLocal() as session:
        publisher = Publisher(name="Test Publisher")
        session.add(publisher)
        session.commit()
        session.refresh(publisher)

        book = Book(
            publisher_id=publisher.id,
            book_name="test-book",
            language="en",
            status=BookStatusEnum.PUBLISHED,
        )
        session.add(book)
        session.commit()
        session.refresh(book)

        return publisher.id, book.id


def _create_sample_job(
    book_id: str = "1",
    publisher_id: str = "1",
    job_type: ProcessingJobType = ProcessingJobType.FULL,
    status: ProcessingStatus = ProcessingStatus.QUEUED,
    priority: JobPriority = JobPriority.NORMAL,
) -> ProcessingJob:
    """Create a sample ProcessingJob for testing."""
    return ProcessingJob(
        job_id="test-job-123",
        book_id=book_id,
        publisher_id=publisher_id,
        job_type=job_type,
        status=status,
        priority=priority,
        progress=0,
        current_step="",
        created_at=datetime.now(timezone.utc),
    )


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
        session.query(Publisher).delete()
        session.query(User).delete()
        session.commit()


# =============================================================================
# Authentication Tests
# =============================================================================


class TestProcessingAuthentication:
    """Test authentication requirements for processing endpoints."""

    def test_trigger_requires_authentication(self) -> None:
        """Test POST /books/{id}/process-ai requires auth."""
        client = TestClient(app)
        response = client.post("/books/1/process-ai", json={})
        assert response.status_code in {401, 403}

    def test_status_requires_authentication(self) -> None:
        """Test GET /books/{id}/process-ai/status requires auth."""
        client = TestClient(app)
        response = client.get("/books/1/process-ai/status")
        assert response.status_code in {401, 403}

    def test_delete_ai_data_requires_authentication(self) -> None:
        """Test DELETE /books/{id}/ai-data requires auth."""
        client = TestClient(app)
        response = client.delete("/books/1/ai-data")
        assert response.status_code in {401, 403}

    def test_invalid_token_is_rejected(self) -> None:
        """Test invalid token returns 401."""
        client = TestClient(app)
        headers = {"Authorization": "Bearer invalid.token.string"}
        response = client.post("/books/1/process-ai", json={}, headers=headers)
        assert response.status_code == 401


# =============================================================================
# Trigger Endpoint Tests
# =============================================================================


class TestTriggerProcessing:
    """Test POST /books/{book_id}/process-ai endpoint."""

    @patch("app.routers.processing.get_queue_service")
    @patch("app.routers.processing._book_has_content")
    @patch("app.routers.processing._check_rate_limit")
    def test_trigger_returns_job_id(
        self,
        mock_rate_limit: MagicMock,
        mock_has_content: MagicMock,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test successful trigger returns 201 with job_id."""
        headers = _create_admin_token()
        publisher_id, book_id = _create_publisher_and_book()

        mock_rate_limit.return_value = (True, 0)
        mock_has_content.return_value = True

        mock_queue = AsyncMock()
        mock_queue.enqueue_job.return_value = _create_sample_job(
            book_id=str(book_id),
            publisher_id=str(publisher_id),
        )
        mock_get_queue.return_value = mock_queue

        client = TestClient(app)
        response = client.post(
            f"/books/{book_id}/process-ai",
            json={},
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert data["job_id"] == "test-job-123"
        assert data["status"] == "queued"

    @patch("app.routers.processing.get_queue_service")
    @patch("app.routers.processing._book_has_content")
    @patch("app.routers.processing._check_rate_limit")
    def test_trigger_with_vocabulary_only(
        self,
        mock_rate_limit: MagicMock,
        mock_has_content: MagicMock,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test trigger with job_type=vocabulary_only."""
        headers = _create_admin_token()
        publisher_id, book_id = _create_publisher_and_book()

        mock_rate_limit.return_value = (True, 0)
        mock_has_content.return_value = True

        mock_queue = AsyncMock()
        mock_queue.enqueue_job.return_value = _create_sample_job(
            book_id=str(book_id),
            publisher_id=str(publisher_id),
            job_type=ProcessingJobType.VOCABULARY_ONLY,
        )
        mock_get_queue.return_value = mock_queue

        client = TestClient(app)
        response = client.post(
            f"/books/{book_id}/process-ai",
            json={"job_type": "vocabulary_only"},
            headers=headers,
        )

        assert response.status_code == 201
        mock_queue.enqueue_job.assert_called_once()
        call_kwargs = mock_queue.enqueue_job.call_args.kwargs
        assert call_kwargs["job_type"] == ProcessingJobType.VOCABULARY_ONLY

    @patch("app.routers.processing.get_queue_service")
    @patch("app.routers.processing._book_has_content")
    @patch("app.routers.processing._check_rate_limit")
    def test_trigger_with_audio_only(
        self,
        mock_rate_limit: MagicMock,
        mock_has_content: MagicMock,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test trigger with job_type=audio_only."""
        headers = _create_admin_token()
        publisher_id, book_id = _create_publisher_and_book()

        mock_rate_limit.return_value = (True, 0)
        mock_has_content.return_value = True

        mock_queue = AsyncMock()
        mock_queue.enqueue_job.return_value = _create_sample_job(
            book_id=str(book_id),
            publisher_id=str(publisher_id),
            job_type=ProcessingJobType.AUDIO_ONLY,
        )
        mock_get_queue.return_value = mock_queue

        client = TestClient(app)
        response = client.post(
            f"/books/{book_id}/process-ai",
            json={"job_type": "audio_only"},
            headers=headers,
        )

        assert response.status_code == 201

    def test_trigger_returns_404_when_book_not_found(self) -> None:
        """Test trigger returns 404 for non-existent book."""
        headers = _create_admin_token()
        client = TestClient(app)

        response = client.post(
            "/books/9999/process-ai",
            json={},
            headers=headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("app.routers.processing._book_has_content")
    def test_trigger_returns_400_when_book_has_no_content(
        self,
        mock_has_content: MagicMock,
    ) -> None:
        """Test trigger returns 400 when book has no content."""
        headers = _create_admin_token()
        _, book_id = _create_publisher_and_book()

        mock_has_content.return_value = False

        client = TestClient(app)
        response = client.post(
            f"/books/{book_id}/process-ai",
            json={},
            headers=headers,
        )

        assert response.status_code == 400
        assert "no content" in response.json()["detail"].lower()

    @patch("app.routers.processing.get_queue_service")
    @patch("app.routers.processing._book_has_content")
    @patch("app.routers.processing._check_rate_limit")
    def test_trigger_returns_409_when_active_job_exists(
        self,
        mock_rate_limit: MagicMock,
        mock_has_content: MagicMock,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test trigger returns 409 when active job exists."""
        headers = _create_admin_token()
        _, book_id = _create_publisher_and_book()

        mock_rate_limit.return_value = (True, 0)
        mock_has_content.return_value = True

        mock_queue = AsyncMock()
        mock_queue.enqueue_job.side_effect = JobAlreadyExistsError(str(book_id))
        mock_get_queue.return_value = mock_queue

        client = TestClient(app)
        response = client.post(
            f"/books/{book_id}/process-ai",
            json={},
            headers=headers,
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()


# =============================================================================
# Rate Limiting Tests
# =============================================================================


class TestRateLimiting:
    """Test rate limiting functionality."""

    @patch("app.routers.processing._book_has_content")
    @patch("app.routers.processing._check_rate_limit")
    def test_rate_limit_returns_429(
        self,
        mock_rate_limit: MagicMock,
        mock_has_content: MagicMock,
    ) -> None:
        """Test rate limiting returns 429 with Retry-After header."""
        headers = _create_admin_token()
        _, book_id = _create_publisher_and_book()

        mock_has_content.return_value = True
        mock_rate_limit.return_value = (False, 3600)  # Rate limited, retry in 1 hour

        client = TestClient(app)
        response = client.post(
            f"/books/{book_id}/process-ai",
            json={},
            headers=headers,
        )

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "3600"

    @patch("app.routers.processing.get_queue_service")
    @patch("app.routers.processing._book_has_content")
    @patch("app.routers.processing._check_rate_limit")
    def test_admin_override_bypasses_rate_limit(
        self,
        mock_rate_limit: MagicMock,
        mock_has_content: MagicMock,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test admin_override bypasses rate limiting."""
        headers = _create_admin_token()
        publisher_id, book_id = _create_publisher_and_book()

        mock_has_content.return_value = True
        # Rate limit would normally block, but admin_override should skip it
        mock_rate_limit.return_value = (False, 3600)

        mock_queue = AsyncMock()
        mock_queue.enqueue_job.return_value = _create_sample_job(
            book_id=str(book_id),
            publisher_id=str(publisher_id),
        )
        mock_get_queue.return_value = mock_queue

        client = TestClient(app)
        response = client.post(
            f"/books/{book_id}/process-ai",
            json={"admin_override": True},
            headers=headers,
        )

        assert response.status_code == 201
        # Rate limit check should not have been called with admin_override
        mock_rate_limit.assert_not_called()


# =============================================================================
# Priority Override Tests
# =============================================================================


class TestPriorityOverride:
    """Test admin priority override functionality."""

    @patch("app.routers.processing.get_queue_service")
    @patch("app.routers.processing._book_has_content")
    @patch("app.routers.processing._check_rate_limit")
    def test_high_priority_with_user_auth(
        self,
        mock_rate_limit: MagicMock,
        mock_has_content: MagicMock,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test HIGH priority is allowed with user authentication."""
        headers = _create_admin_token()
        publisher_id, book_id = _create_publisher_and_book()

        mock_rate_limit.return_value = (True, 0)
        mock_has_content.return_value = True

        mock_queue = AsyncMock()
        mock_queue.enqueue_job.return_value = _create_sample_job(
            book_id=str(book_id),
            publisher_id=str(publisher_id),
            priority=JobPriority.HIGH,
        )
        mock_get_queue.return_value = mock_queue

        client = TestClient(app)
        response = client.post(
            f"/books/{book_id}/process-ai",
            json={"priority": "high"},
            headers=headers,
        )

        assert response.status_code == 201
        call_kwargs = mock_queue.enqueue_job.call_args.kwargs
        assert call_kwargs["priority"] == JobPriority.HIGH


# =============================================================================
# Status Endpoint Tests
# =============================================================================


class TestProcessingStatus:
    """Test GET /books/{book_id}/process-ai/status endpoint."""

    @patch("app.routers.processing.get_queue_service")
    def test_status_returns_job_details(
        self,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test status endpoint returns job details."""
        headers = _create_admin_token()
        publisher_id, book_id = _create_publisher_and_book()

        mock_queue = AsyncMock()
        mock_queue.list_jobs.return_value = [
            _create_sample_job(
                book_id=str(book_id),
                publisher_id=str(publisher_id),
                status=ProcessingStatus.PROCESSING,
            )
        ]
        mock_get_queue.return_value = mock_queue

        client = TestClient(app)
        response = client.get(
            f"/books/{book_id}/process-ai/status",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "test-job-123"
        assert data["status"] == "processing"

    @patch("app.routers.processing.get_queue_service")
    def test_status_returns_404_when_no_jobs(
        self,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test status returns 404 when no jobs exist for book."""
        headers = _create_admin_token()
        _, book_id = _create_publisher_and_book()

        mock_queue = AsyncMock()
        mock_queue.list_jobs.return_value = []
        mock_get_queue.return_value = mock_queue

        client = TestClient(app)
        response = client.get(
            f"/books/{book_id}/process-ai/status",
            headers=headers,
        )

        assert response.status_code == 404
        assert "no processing jobs" in response.json()["detail"].lower()

    def test_status_returns_404_when_book_not_found(self) -> None:
        """Test status returns 404 for non-existent book."""
        headers = _create_admin_token()
        client = TestClient(app)

        response = client.get(
            "/books/9999/process-ai/status",
            headers=headers,
        )

        assert response.status_code == 404


# =============================================================================
# Delete AI Data Tests
# =============================================================================


class TestDeleteAIData:
    """Test DELETE /books/{book_id}/ai-data endpoint."""

    @patch("app.routers.processing.get_ai_data_cleanup_manager")
    def test_delete_ai_data_returns_stats(
        self,
        mock_get_cleanup: MagicMock,
    ) -> None:
        """Test DELETE returns cleanup statistics."""
        headers = _create_admin_token()
        _, book_id = _create_publisher_and_book()

        mock_cleanup = MagicMock()
        mock_cleanup.cleanup_all.return_value = MagicMock(
            total_deleted=10,
            text_deleted=5,
            modules_deleted=3,
            audio_deleted=2,
            vocabulary_deleted=0,
            metadata_deleted=0,
            errors=[],
        )
        mock_get_cleanup.return_value = mock_cleanup

        client = TestClient(app)
        response = client.delete(
            f"/books/{book_id}/ai-data",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_deleted"] == 10
        assert data["text_deleted"] == 5
        assert data["modules_deleted"] == 3
        assert data["audio_deleted"] == 2

    @patch("app.routers.processing.get_queue_service")
    @patch("app.routers.processing.get_ai_data_cleanup_manager")
    @patch("app.routers.processing._book_has_content")
    def test_delete_with_reprocess_triggers_new_job(
        self,
        mock_has_content: MagicMock,
        mock_get_cleanup: MagicMock,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test DELETE with reprocess=true triggers new processing job."""
        headers = _create_admin_token()
        publisher_id, book_id = _create_publisher_and_book()

        mock_has_content.return_value = True

        mock_cleanup = MagicMock()
        mock_cleanup.cleanup_all.return_value = MagicMock(
            total_deleted=5,
            text_deleted=2,
            modules_deleted=1,
            audio_deleted=1,
            vocabulary_deleted=1,
            metadata_deleted=0,
            errors=[],
        )
        mock_get_cleanup.return_value = mock_cleanup

        mock_queue = AsyncMock()
        mock_queue.enqueue_job.return_value = _create_sample_job(
            book_id=str(book_id),
            publisher_id=str(publisher_id),
        )
        mock_get_queue.return_value = mock_queue

        client = TestClient(app)
        response = client.delete(
            f"/books/{book_id}/ai-data?reprocess=true",
            headers=headers,
        )

        assert response.status_code == 200
        mock_queue.enqueue_job.assert_called_once()

    def test_delete_returns_404_when_book_not_found(self) -> None:
        """Test DELETE returns 404 for non-existent book."""
        headers = _create_admin_token()
        client = TestClient(app)

        response = client.delete(
            "/books/9999/ai-data",
            headers=headers,
        )

        assert response.status_code == 404
