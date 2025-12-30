"""Integration tests for AI data retrieval API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_data.models import (
    ProcessingMetadata,
    ProcessingStatus,
    StageResult,
    StageStatus,
)


def _create_mock_user() -> MagicMock:
    """Create a mock user object."""
    user = MagicMock()
    user.id = 1
    user.email = "admin@example.com"
    return user


def _create_mock_book(
    book_id: int = 1,
    publisher_name: str = "Test Publisher",
    book_name: str = "test-book",
) -> MagicMock:
    """Create a mock book object."""
    book = MagicMock()
    book.id = book_id
    book.publisher = publisher_name
    book.book_name = book_name
    return book


def _create_sample_metadata(
    book_id: str = "1",
    publisher_id: str = "Test Publisher",
    book_name: str = "test-book",
    status: ProcessingStatus = ProcessingStatus.COMPLETED,
) -> ProcessingMetadata:
    """Create sample ProcessingMetadata for testing."""
    return ProcessingMetadata(
        book_id=book_id,
        publisher_id=publisher_id,
        book_name=book_name,
        processing_status=status,
        processing_started_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        processing_completed_at=datetime(2024, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
        total_pages=120,
        total_modules=8,
        total_vocabulary=150,
        total_audio_files=300,
        languages=["en", "tr"],
        primary_language="en",
        difficulty_range=["A1", "A2", "B1"],
        stages={
            "text_extraction": StageResult(
                status=StageStatus.COMPLETED,
                completed_at=datetime(2024, 1, 15, 10, 10, 0, tzinfo=timezone.utc),
            ),
            "segmentation": StageResult(
                status=StageStatus.COMPLETED,
                completed_at=datetime(2024, 1, 15, 10, 20, 0, tzinfo=timezone.utc),
            ),
        },
        errors=[],
    )


def _create_sample_modules() -> list[dict]:
    """Create sample module list for testing."""
    return [
        {
            "module_id": 1,
            "title": "Unit 1: Greetings",
            "pages": [1, 2, 3, 4, 5],
            "text": "Hello and welcome to unit 1...",
            "topics": ["greetings", "introductions"],
            "vocabulary_ids": ["hello", "goodbye"],
            "language": "en",
            "difficulty": "A1",
            "word_count": 450,
            "extracted_at": "2024-01-15T10:30:00Z",
        },
        {
            "module_id": 2,
            "title": "Unit 2: Family",
            "pages": [6, 7, 8, 9, 10],
            "text": "In this unit we learn about family...",
            "topics": ["family", "relationships"],
            "vocabulary_ids": ["mother", "father"],
            "language": "en",
            "difficulty": "A1",
            "word_count": 520,
            "extracted_at": "2024-01-15T10:30:00Z",
        },
    ]


def _create_sample_vocabulary() -> dict:
    """Create sample vocabulary data for testing."""
    return {
        "language": "en",
        "translation_language": "tr",
        "total_words": 2,
        "words": [
            {
                "id": "hello",
                "word": "hello",
                "translation": "merhaba",
                "definition": "a greeting",
                "part_of_speech": "interjection",
                "level": "A1",
                "example": "Hello, how are you?",
                "module_id": 1,
                "page": 1,
                "audio": {
                    "word": "audio/vocabulary/en/hello.mp3",
                    "translation": "audio/vocabulary/tr/merhaba.mp3",
                },
            },
            {
                "id": "goodbye",
                "word": "goodbye",
                "translation": "hoşçakal",
                "definition": "a farewell",
                "part_of_speech": "interjection",
                "level": "A1",
                "example": "Goodbye, see you tomorrow!",
                "module_id": 1,
                "page": 5,
                "audio": {
                    "word": "audio/vocabulary/en/goodbye.mp3",
                    "translation": "audio/vocabulary/tr/hoscakal.mp3",
                },
            },
        ],
        "extracted_at": "2024-01-15T10:30:00Z",
    }


# =============================================================================
# Authentication Tests
# =============================================================================


class TestAIDataAuthentication:
    """Test authentication requirements for AI data endpoints."""

    def test_metadata_requires_authentication(self) -> None:
        """Test GET /books/{id}/ai-data/metadata requires auth."""
        client = TestClient(app)
        response = client.get("/books/1/ai-data/metadata")
        assert response.status_code in {401, 403}

    def test_modules_requires_authentication(self) -> None:
        """Test GET /books/{id}/ai-data/modules requires auth."""
        client = TestClient(app)
        response = client.get("/books/1/ai-data/modules")
        assert response.status_code in {401, 403}

    def test_module_detail_requires_authentication(self) -> None:
        """Test GET /books/{id}/ai-data/modules/{module_id} requires auth."""
        client = TestClient(app)
        response = client.get("/books/1/ai-data/modules/1")
        assert response.status_code in {401, 403}

    def test_vocabulary_requires_authentication(self) -> None:
        """Test GET /books/{id}/ai-data/vocabulary requires auth."""
        client = TestClient(app)
        response = client.get("/books/1/ai-data/vocabulary")
        assert response.status_code in {401, 403}

    def test_audio_requires_authentication(self) -> None:
        """Test GET /books/{id}/ai-data/audio/vocabulary/{lang}/{word}.mp3 requires auth."""
        client = TestClient(app)
        response = client.get("/books/1/ai-data/audio/vocabulary/en/hello.mp3")
        assert response.status_code in {401, 403}

    @patch("app.routers.ai_data._require_auth")
    def test_invalid_token_is_rejected(
        self,
        mock_auth: MagicMock,
    ) -> None:
        """Test invalid token returns 401."""
        from fastapi import HTTPException

        mock_auth.side_effect = HTTPException(status_code=401, detail="Invalid token")

        client = TestClient(app)
        headers = {"Authorization": "Bearer invalid.token.string"}
        response = client.get("/books/1/ai-data/metadata", headers=headers)
        assert response.status_code == 401


# =============================================================================
# Metadata Endpoint Tests
# =============================================================================


class TestGetMetadata:
    """Test GET /books/{book_id}/ai-data/metadata endpoint."""

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_metadata_returns_processing_info(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test metadata endpoint returns processing info."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.get_metadata.return_value = _create_sample_metadata()
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/1/ai-data/metadata", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["book_id"] == "1"
        assert data["processing_status"] == "completed"
        assert data["total_pages"] == 120
        assert data["total_modules"] == 8
        assert data["total_vocabulary"] == 150
        assert data["total_audio_files"] == 300
        assert "en" in data["languages"]
        assert "Cache-Control" in response.headers

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_metadata_returns_404_when_not_processed(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test metadata returns 404 when book not processed."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.get_metadata.return_value = None
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/1/ai-data/metadata", headers=headers)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    def test_metadata_returns_404_when_book_not_found(
        self,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test metadata returns 404 for non-existent book."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = None

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/9999/ai-data/metadata", headers=headers)

        assert response.status_code == 404


# =============================================================================
# Modules Endpoint Tests
# =============================================================================


class TestGetModules:
    """Test GET /books/{book_id}/ai-data/modules endpoint."""

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_modules_returns_list(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test modules endpoint returns list of modules."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.list_modules.return_value = _create_sample_modules()
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/1/ai-data/modules", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["book_id"] == "1"
        assert data["total_modules"] == 2
        assert len(data["modules"]) == 2
        assert data["modules"][0]["module_id"] == 1
        assert data["modules"][0]["title"] == "Unit 1: Greetings"
        assert "Cache-Control" in response.headers

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_modules_returns_404_when_no_modules(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test modules returns 404 when no modules exist."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.list_modules.return_value = None
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/1/ai-data/modules", headers=headers)

        assert response.status_code == 404

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    def test_modules_returns_404_when_book_not_found(
        self,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test modules returns 404 for non-existent book."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = None

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/9999/ai-data/modules", headers=headers)

        assert response.status_code == 404


class TestGetModuleDetail:
    """Test GET /books/{book_id}/ai-data/modules/{module_id} endpoint."""

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_module_returns_full_data(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test module detail endpoint returns full module data."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.get_module.return_value = _create_sample_modules()[0]
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/1/ai-data/modules/1", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["module_id"] == 1
        assert data["title"] == "Unit 1: Greetings"
        assert data["text"] == "Hello and welcome to unit 1..."
        assert "greetings" in data["topics"]
        assert "hello" in data["vocabulary_ids"]
        assert "Cache-Control" in response.headers

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_module_returns_404_for_invalid_id(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test module detail returns 404 for invalid module_id."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.get_module.return_value = None
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/1/ai-data/modules/999", headers=headers)

        assert response.status_code == 404
        assert "999" in response.json()["detail"]


# =============================================================================
# Vocabulary Endpoint Tests
# =============================================================================


class TestGetVocabulary:
    """Test GET /books/{book_id}/ai-data/vocabulary endpoint."""

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_vocabulary_returns_words(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test vocabulary endpoint returns words array."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.get_vocabulary.return_value = _create_sample_vocabulary()
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/1/ai-data/vocabulary", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["book_id"] == "1"
        assert data["language"] == "en"
        assert data["translation_language"] == "tr"
        assert data["total_words"] == 2
        assert len(data["words"]) == 2
        assert data["words"][0]["word"] == "hello"
        assert data["words"][0]["translation"] == "merhaba"
        assert "Cache-Control" in response.headers

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_vocabulary_filters_by_module(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test vocabulary with module filter."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        # Return vocabulary filtered to module 1
        filtered_vocab = _create_sample_vocabulary()
        mock_service = MagicMock()
        mock_service.get_vocabulary.return_value = filtered_vocab
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/1/ai-data/vocabulary?module=1", headers=headers)

        assert response.status_code == 200
        # Verify filter parameter was passed
        mock_service.get_vocabulary.assert_called_once()
        call_kwargs = mock_service.get_vocabulary.call_args.kwargs
        assert call_kwargs.get("module_id") == 1

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_vocabulary_returns_404_when_not_processed(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test vocabulary returns 404 when not processed."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.get_vocabulary.return_value = None
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/1/ai-data/vocabulary", headers=headers)

        assert response.status_code == 404


# =============================================================================
# Audio URL Endpoint Tests
# =============================================================================


class TestGetAudioUrl:
    """Test GET /books/{book_id}/ai-data/audio/vocabulary/{lang}/{word}.mp3 endpoint."""

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_audio_returns_presigned_url(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test audio endpoint returns presigned URL."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.get_audio_url.return_value = "https://minio.example.com/presigned-url"
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get(
            "/books/1/ai-data/audio/vocabulary/en/hello.mp3", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["word"] == "hello"
        assert data["language"] == "en"
        assert data["url"] == "https://minio.example.com/presigned-url"
        assert data["expires_in"] == 3600
        assert "Cache-Control" in response.headers

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_audio_returns_404_for_nonexistent_file(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test audio returns 404 for non-existent file."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.get_audio_url.return_value = None
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get(
            "/books/1/ai-data/audio/vocabulary/en/nonexistent.mp3", headers=headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    def test_audio_returns_400_for_invalid_language(
        self,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test audio returns 400 for unsupported language."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get(
            "/books/1/ai-data/audio/vocabulary/invalid/hello.mp3", headers=headers
        )

        assert response.status_code == 400
        assert "unsupported language" in response.json()["detail"].lower()

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    def test_audio_returns_400_for_invalid_word_format(
        self,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test audio returns 400 for invalid word format."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        # Test with path traversal attempt
        response = client.get(
            "/books/1/ai-data/audio/vocabulary/en/hello%2F..%2F..%2Fetc.mp3",
            headers=headers,
        )

        # Should return 400 for invalid format (contains path separators)
        assert response.status_code in {400, 404}


# =============================================================================
# Cache-Control Header Tests
# =============================================================================


class TestCacheHeaders:
    """Test Cache-Control headers are present in responses."""

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_metadata_has_cache_control(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test metadata response has Cache-Control header."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.get_metadata.return_value = _create_sample_metadata()
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/1/ai-data/metadata", headers=headers)

        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        assert "max-age" in response.headers["Cache-Control"]

    @patch("app.routers.ai_data._require_auth")
    @patch("app.routers.ai_data._book_repository")
    @patch("app.routers.ai_data.get_ai_data_retrieval_service")
    def test_modules_has_cache_control(
        self,
        mock_get_service: MagicMock,
        mock_book_repo: MagicMock,
        mock_auth: MagicMock,
    ) -> None:
        """Test modules response has Cache-Control header."""
        mock_auth.return_value = 1
        mock_book_repo.get_by_id.return_value = _create_mock_book()

        mock_service = MagicMock()
        mock_service.list_modules.return_value = _create_sample_modules()
        mock_get_service.return_value = mock_service

        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}
        response = client.get("/books/1/ai-data/modules", headers=headers)

        assert response.status_code == 200
        assert "Cache-Control" in response.headers
        assert "max-age" in response.headers["Cache-Control"]
