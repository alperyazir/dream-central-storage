"""Tests for the AI data storage service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from minio.error import S3Error

from app.services.ai_data.models import (
    AIDataStorageError,
    AIDataStructure,
    CleanupError,
    CleanupStats,
    InitializationError,
    MetadataError,
    ProcessingMetadata,
    ProcessingStatus,
    StageResult,
    StageStatus,
)
from app.services.ai_data.service import AIDataMetadataService
from app.services.ai_data.structure import AIDataStructureManager
from app.services.ai_data.cleanup import AIDataCleanupManager


# =============================================================================
# Test Data Models
# =============================================================================


class TestProcessingStatus:
    """Tests for ProcessingStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        assert ProcessingStatus.PENDING == "pending"
        assert ProcessingStatus.PROCESSING == "processing"
        assert ProcessingStatus.COMPLETED == "completed"
        assert ProcessingStatus.PARTIAL == "partial"
        assert ProcessingStatus.FAILED == "failed"


class TestStageStatus:
    """Tests for StageStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses exist."""
        assert StageStatus.PENDING == "pending"
        assert StageStatus.RUNNING == "running"
        assert StageStatus.COMPLETED == "completed"
        assert StageStatus.FAILED == "failed"
        assert StageStatus.SKIPPED == "skipped"


class TestStageResult:
    """Tests for StageResult dataclass."""

    def test_create_stage_result(self):
        """Test creating a stage result."""
        result = StageResult(
            status=StageStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            data={"total_pages": 100},
        )
        assert result.status == StageStatus.COMPLETED
        assert result.completed_at is not None
        assert result.data["total_pages"] == 100

    def test_to_dict(self):
        """Test converting stage result to dictionary."""
        now = datetime.now(timezone.utc)
        result = StageResult(
            status=StageStatus.COMPLETED,
            completed_at=now,
            data={"module_count": 5},
        )
        d = result.to_dict()
        assert d["status"] == "completed"
        assert d["completed_at"] == now.isoformat()
        assert d["module_count"] == 5

    def test_to_dict_with_error(self):
        """Test converting failed stage result to dictionary."""
        result = StageResult(
            status=StageStatus.FAILED,
            error_message="Something went wrong",
        )
        d = result.to_dict()
        assert d["status"] == "failed"
        assert d["error_message"] == "Something went wrong"

    def test_from_dict(self):
        """Test creating stage result from dictionary."""
        data = {
            "status": "completed",
            "completed_at": "2024-01-15T10:30:00+00:00",
            "total_pages": 120,
            "method": "native",
        }
        result = StageResult.from_dict(data)
        assert result.status == StageStatus.COMPLETED
        assert result.completed_at is not None
        assert result.data["total_pages"] == 120
        assert result.data["method"] == "native"


class TestProcessingMetadata:
    """Tests for ProcessingMetadata dataclass."""

    def test_create_metadata(self):
        """Test creating processing metadata."""
        metadata = ProcessingMetadata(
            book_id="test-book",
            publisher_id="test-publisher",
            book_name="test-book-name",
            processing_status=ProcessingStatus.PROCESSING,
        )
        assert metadata.book_id == "test-book"
        assert metadata.processing_status == ProcessingStatus.PROCESSING
        assert metadata.total_pages == 0
        assert metadata.stages == {}

    def test_to_dict(self):
        """Test converting metadata to dictionary."""
        now = datetime.now(timezone.utc)
        metadata = ProcessingMetadata(
            book_id="test-book",
            publisher_id="test-publisher",
            book_name="test-book-name",
            processing_status=ProcessingStatus.COMPLETED,
            processing_started_at=now,
            processing_completed_at=now,
            total_pages=100,
            total_modules=5,
            total_vocabulary=150,
            total_audio_files=300,
            languages=["en", "tr"],
            primary_language="en",
            llm_provider="deepseek",
            tts_provider="edge",
        )
        d = metadata.to_dict()
        assert d["book_id"] == "test-book"
        assert d["processing_status"] == "completed"
        assert d["total_pages"] == 100
        assert d["total_modules"] == 5
        assert d["total_vocabulary"] == 150
        assert d["total_audio_files"] == 300
        assert d["languages"] == ["en", "tr"]
        assert d["llm_provider"] == "deepseek"
        assert d["tts_provider"] == "edge"

    def test_from_dict(self):
        """Test creating metadata from dictionary."""
        data = {
            "book_id": "test-book",
            "publisher_id": "test-publisher",
            "book_name": "test-book-name",
            "processing_status": "completed",
            "processing_started_at": "2024-01-15T10:00:00+00:00",
            "processing_completed_at": "2024-01-15T10:30:00+00:00",
            "total_pages": 100,
            "total_modules": 5,
            "total_vocabulary": 150,
            "total_audio_files": 300,
            "languages": ["en", "tr"],
            "primary_language": "en",
            "difficulty_range": ["A1", "A2"],
            "llm_provider": "deepseek",
            "tts_provider": "edge",
            "stages": {
                "text_extraction": {
                    "status": "completed",
                    "completed_at": "2024-01-15T10:10:00+00:00",
                    "total_pages": 100,
                }
            },
            "errors": [],
        }
        metadata = ProcessingMetadata.from_dict(data)
        assert metadata.book_id == "test-book"
        assert metadata.processing_status == ProcessingStatus.COMPLETED
        assert metadata.total_pages == 100
        assert len(metadata.stages) == 1
        assert "text_extraction" in metadata.stages


class TestAIDataStructure:
    """Tests for AIDataStructure dataclass."""

    def test_from_book_info(self):
        """Test creating structure from book info."""
        structure = AIDataStructure.from_book_info(
            publisher_id="pub-123",
            book_id="book-456",
            book_name="my-book",
        )
        # Note: book_id is not in the path, only publisher_id and book_name
        assert structure.base_path == "pub-123/books/my-book/ai-data"
        assert structure.text_path == "pub-123/books/my-book/ai-data/text"
        assert structure.modules_path == "pub-123/books/my-book/ai-data/modules"
        assert structure.vocabulary_path == "pub-123/books/my-book/ai-data/vocabulary.json"
        assert structure.audio_path == "pub-123/books/my-book/ai-data/audio"
        assert structure.metadata_path == "pub-123/books/my-book/ai-data/metadata.json"

    def test_get_all_directories(self):
        """Test getting all directory paths."""
        structure = AIDataStructure.from_book_info("pub", "book", "name")
        dirs = structure.get_all_directories()
        assert len(dirs) == 5
        assert structure.base_path in dirs
        assert structure.text_path in dirs
        assert structure.modules_path in dirs
        assert structure.audio_path in dirs


class TestCleanupStats:
    """Tests for CleanupStats dataclass."""

    def test_create_cleanup_stats(self):
        """Test creating cleanup stats."""
        stats = CleanupStats(
            total_deleted=100,
            text_deleted=20,
            modules_deleted=10,
            audio_deleted=68,
            vocabulary_deleted=1,
            metadata_deleted=1,
        )
        assert stats.total_deleted == 100
        assert stats.text_deleted == 20
        assert stats.audio_deleted == 68

    def test_to_dict(self):
        """Test converting stats to dictionary."""
        stats = CleanupStats(total_deleted=50)
        d = stats.to_dict()
        assert d["total_deleted"] == 50
        assert d["errors"] == []


# =============================================================================
# Test Exceptions
# =============================================================================


class TestExceptions:
    """Tests for exception classes."""

    def test_ai_data_storage_error(self):
        """Test base exception."""
        error = AIDataStorageError("Test error", "book-123", {"key": "value"})
        assert "book-123" in str(error)
        assert "Test error" in str(error)
        assert error.details["key"] == "value"

    def test_metadata_error(self):
        """Test metadata error."""
        error = MetadataError("book-123", "create", "File not found")
        assert "create" in str(error)
        assert error.operation == "create"
        assert error.reason == "File not found"

    def test_initialization_error(self):
        """Test initialization error."""
        error = InitializationError("book-123", "/ai-data/text", "Permission denied")
        assert "/ai-data/text" in str(error)
        assert error.path == "/ai-data/text"

    def test_cleanup_error(self):
        """Test cleanup error."""
        error = CleanupError("book-123", "/ai-data/", "Failed to delete")
        assert "/ai-data/" in str(error)
        assert error.path == "/ai-data/"


# =============================================================================
# Test AIDataMetadataService
# =============================================================================


class TestAIDataMetadataService:
    """Tests for AIDataMetadataService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.minio_publishers_bucket = "publishers"
        settings.llm_primary_provider = "deepseek"
        settings.tts_primary_provider = "edge"
        return settings

    @pytest.fixture
    def mock_minio_client(self):
        """Create mock MinIO client."""
        return MagicMock()

    def test_build_metadata_path(self, mock_settings):
        """Test building metadata path."""
        service = AIDataMetadataService(settings=mock_settings)
        path = service._build_metadata_path("pub-123", "book-456", "my-book")
        # Note: book_id is not in the path, only publisher_id and book_name
        assert path == "pub-123/books/my-book/ai-data/metadata.json"

    @patch("app.services.ai_data.service.get_minio_client")
    def test_create_metadata(self, mock_get_client, mock_settings, mock_minio_client):
        """Test creating initial metadata."""
        mock_get_client.return_value = mock_minio_client

        service = AIDataMetadataService(settings=mock_settings)
        metadata = service.create_metadata(
            book_id="book-123",
            publisher_id="pub-456",
            book_name="test-book",
        )

        assert metadata.book_id == "book-123"
        assert metadata.processing_status == ProcessingStatus.PROCESSING
        assert metadata.llm_provider == "deepseek"
        assert metadata.tts_provider == "edge"
        assert len(metadata.stages) == 6
        assert "text_extraction" in metadata.stages

        # Verify MinIO put_object was called
        mock_minio_client.put_object.assert_called_once()

    @patch("app.services.ai_data.service.get_minio_client")
    def test_get_metadata_not_found(self, mock_get_client, mock_settings, mock_minio_client):
        """Test getting metadata when it doesn't exist."""
        mock_get_client.return_value = mock_minio_client
        mock_minio_client.get_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Key not found",
            resource="metadata.json",
            request_id="123",
            host_id="host",
            response=MagicMock(),
        )

        service = AIDataMetadataService(settings=mock_settings)
        result = service.get_metadata("pub", "book", "name")

        assert result is None

    @patch("app.services.ai_data.service.get_minio_client")
    def test_get_metadata_success(self, mock_get_client, mock_settings, mock_minio_client):
        """Test getting existing metadata."""
        mock_get_client.return_value = mock_minio_client

        # Mock response
        metadata_dict = {
            "book_id": "book-123",
            "publisher_id": "pub-456",
            "book_name": "test-book",
            "processing_status": "completed",
            "total_pages": 100,
            "stages": {},
            "errors": [],
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(metadata_dict).encode("utf-8")
        mock_minio_client.get_object.return_value = mock_response

        service = AIDataMetadataService(settings=mock_settings)
        result = service.get_metadata("pub-456", "book-123", "test-book")

        assert result is not None
        assert result.book_id == "book-123"
        assert result.processing_status == ProcessingStatus.COMPLETED
        assert result.total_pages == 100

    @patch("app.services.ai_data.service.get_minio_client")
    def test_update_metadata_text_extraction(self, mock_get_client, mock_settings, mock_minio_client):
        """Test updating metadata with text extraction results."""
        mock_get_client.return_value = mock_minio_client

        # Mock existing metadata
        existing = {
            "book_id": "book-123",
            "publisher_id": "pub-456",
            "book_name": "test-book",
            "processing_status": "processing",
            "stages": {},
            "errors": [],
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(existing).encode("utf-8")
        mock_minio_client.get_object.return_value = mock_response

        service = AIDataMetadataService(settings=mock_settings)
        result = service.update_metadata(
            publisher_id="pub-456",
            book_id="book-123",
            book_name="test-book",
            stage_name="text_extraction",
            stage_result={"total_pages": 120, "method": "native"},
            success=True,
        )

        assert result.total_pages == 120
        assert "text_extraction" in result.stages
        assert result.stages["text_extraction"].status == StageStatus.COMPLETED

    @patch("app.services.ai_data.service.get_minio_client")
    def test_finalize_metadata_completed(self, mock_get_client, mock_settings, mock_minio_client):
        """Test finalizing metadata with completed status."""
        mock_get_client.return_value = mock_minio_client

        # Mock existing metadata
        existing = {
            "book_id": "book-123",
            "publisher_id": "pub-456",
            "book_name": "test-book",
            "processing_status": "processing",
            "stages": {},
            "errors": [],
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(existing).encode("utf-8")
        mock_minio_client.get_object.return_value = mock_response

        service = AIDataMetadataService(settings=mock_settings)
        result = service.finalize_metadata(
            publisher_id="pub-456",
            book_id="book-123",
            book_name="test-book",
            final_status=ProcessingStatus.COMPLETED,
        )

        assert result.processing_status == ProcessingStatus.COMPLETED
        assert result.processing_completed_at is not None

    @patch("app.services.ai_data.service.get_minio_client")
    def test_finalize_metadata_failed(self, mock_get_client, mock_settings, mock_minio_client):
        """Test finalizing metadata with failed status."""
        mock_get_client.return_value = mock_minio_client

        # Mock existing metadata
        existing = {
            "book_id": "book-123",
            "publisher_id": "pub-456",
            "book_name": "test-book",
            "processing_status": "processing",
            "stages": {},
            "errors": [],
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(existing).encode("utf-8")
        mock_minio_client.get_object.return_value = mock_response

        service = AIDataMetadataService(settings=mock_settings)
        result = service.finalize_metadata(
            publisher_id="pub-456",
            book_id="book-123",
            book_name="test-book",
            final_status=ProcessingStatus.FAILED,
            error_message="Critical failure",
        )

        assert result.processing_status == ProcessingStatus.FAILED
        assert len(result.errors) == 1
        assert result.errors[0]["error"] == "Critical failure"

    @patch("app.services.ai_data.service.get_minio_client")
    def test_metadata_exists_true(self, mock_get_client, mock_settings, mock_minio_client):
        """Test checking if metadata exists."""
        mock_get_client.return_value = mock_minio_client

        service = AIDataMetadataService(settings=mock_settings)
        result = service.metadata_exists("pub", "book", "name")

        assert result is True
        mock_minio_client.stat_object.assert_called_once()

    @patch("app.services.ai_data.service.get_minio_client")
    def test_metadata_exists_false(self, mock_get_client, mock_settings, mock_minio_client):
        """Test checking if metadata doesn't exist."""
        mock_get_client.return_value = mock_minio_client
        mock_minio_client.stat_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Key not found",
            resource="metadata.json",
            request_id="123",
            host_id="host",
            response=MagicMock(),
        )

        service = AIDataMetadataService(settings=mock_settings)
        result = service.metadata_exists("pub", "book", "name")

        assert result is False


# =============================================================================
# Test AIDataStructureManager
# =============================================================================


class TestAIDataStructureManager:
    """Tests for AIDataStructureManager."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.minio_publishers_bucket = "publishers"
        return settings

    @pytest.fixture
    def mock_minio_client(self):
        """Create mock MinIO client."""
        return MagicMock()

    def test_get_ai_data_paths(self, mock_settings):
        """Test getting all AI data paths."""
        manager = AIDataStructureManager(settings=mock_settings)
        structure = manager.get_ai_data_paths("pub-123", "book-456", "my-book")
        # Note: book_id is not in the path, only publisher_id and book_name
        assert structure.base_path == "pub-123/books/my-book/ai-data"
        assert "text" in structure.text_path
        assert "modules" in structure.modules_path

    @patch("app.services.ai_data.structure.get_minio_client")
    def test_initialize_ai_data_structure(self, mock_get_client, mock_settings, mock_minio_client):
        """Test initializing AI data structure."""
        mock_get_client.return_value = mock_minio_client
        # Simulate directories don't exist
        mock_minio_client.stat_object.side_effect = S3Error(
            code="NoSuchKey",
            message="Key not found",
            resource="test",
            request_id="123",
            host_id="host",
            response=MagicMock(),
        )

        manager = AIDataStructureManager(settings=mock_settings)
        structure = manager.initialize_ai_data_structure("pub", "book", "name")

        assert structure is not None
        # Verify put_object was called for each directory
        assert mock_minio_client.put_object.call_count == 5

    @patch("app.services.ai_data.structure.get_minio_client")
    def test_verify_structure(self, mock_get_client, mock_settings, mock_minio_client):
        """Test verifying AI data structure."""
        mock_get_client.return_value = mock_minio_client
        mock_minio_client.list_objects.return_value = [MagicMock()]

        manager = AIDataStructureManager(settings=mock_settings)
        result = manager.verify_structure("pub", "book", "name")

        assert isinstance(result, dict)
        assert all(v is True for v in result.values())

    @patch("app.services.ai_data.structure.get_minio_client")
    def test_structure_exists_true(self, mock_get_client, mock_settings, mock_minio_client):
        """Test checking if structure exists."""
        mock_get_client.return_value = mock_minio_client
        mock_minio_client.list_objects.return_value = [MagicMock()]

        manager = AIDataStructureManager(settings=mock_settings)
        result = manager.structure_exists("pub", "book", "name")

        assert result is True

    @patch("app.services.ai_data.structure.get_minio_client")
    def test_structure_exists_false(self, mock_get_client, mock_settings, mock_minio_client):
        """Test checking if structure doesn't exist."""
        mock_get_client.return_value = mock_minio_client
        mock_minio_client.list_objects.return_value = []

        manager = AIDataStructureManager(settings=mock_settings)
        result = manager.structure_exists("pub", "book", "name")

        assert result is False


# =============================================================================
# Test AIDataCleanupManager
# =============================================================================


class TestAIDataCleanupManager:
    """Tests for AIDataCleanupManager."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.minio_publishers_bucket = "publishers"
        return settings

    @pytest.fixture
    def mock_minio_client(self):
        """Create mock MinIO client."""
        return MagicMock()

    @patch("app.services.ai_data.cleanup.get_minio_client")
    def test_cleanup_all(self, mock_get_client, mock_settings, mock_minio_client):
        """Test cleaning up all AI data."""
        mock_get_client.return_value = mock_minio_client

        # Mock objects to delete
        mock_obj1 = MagicMock()
        mock_obj1.object_name = "pub/books/book/name/ai-data/text/page_001.txt"
        mock_obj2 = MagicMock()
        mock_obj2.object_name = "pub/books/book/name/ai-data/modules/module_1.json"
        mock_obj3 = MagicMock()
        mock_obj3.object_name = "pub/books/book/name/ai-data/vocabulary.json"
        mock_obj4 = MagicMock()
        mock_obj4.object_name = "pub/books/book/name/ai-data/audio/vocabulary/en/hello.mp3"
        mock_obj5 = MagicMock()
        mock_obj5.object_name = "pub/books/book/name/ai-data/metadata.json"

        mock_minio_client.list_objects.return_value = [
            mock_obj1, mock_obj2, mock_obj3, mock_obj4, mock_obj5
        ]

        manager = AIDataCleanupManager(settings=mock_settings)
        stats = manager.cleanup_all("pub", "book", "name")

        assert stats.total_deleted == 5
        assert stats.text_deleted == 1
        assert stats.modules_deleted == 1
        assert stats.vocabulary_deleted == 1
        assert stats.audio_deleted == 1
        assert stats.metadata_deleted == 1
        assert len(stats.errors) == 0

    @patch("app.services.ai_data.cleanup.get_minio_client")
    def test_cleanup_selective_text_only(self, mock_get_client, mock_settings, mock_minio_client):
        """Test selective cleanup of text directory only."""
        mock_get_client.return_value = mock_minio_client

        # Mock text objects
        mock_obj1 = MagicMock()
        mock_obj1.object_name = "pub/books/book/name/ai-data/text/page_001.txt"
        mock_obj2 = MagicMock()
        mock_obj2.object_name = "pub/books/book/name/ai-data/text/page_002.txt"

        mock_minio_client.list_objects.return_value = [mock_obj1, mock_obj2]

        manager = AIDataCleanupManager(settings=mock_settings)
        stats = manager.cleanup_selective("pub", "book", "name", ["text"])

        assert stats.total_deleted == 2
        assert stats.text_deleted == 2
        assert stats.modules_deleted == 0

    @patch("app.services.ai_data.cleanup.get_minio_client")
    def test_get_cleanup_stats(self, mock_get_client, mock_settings, mock_minio_client):
        """Test getting cleanup stats without deleting."""
        mock_get_client.return_value = mock_minio_client

        # Mock different counts for different directories
        def list_objects_side_effect(bucket, prefix, recursive=False):
            if "/text/" in prefix:
                return [MagicMock() for _ in range(10)]
            elif "/modules/" in prefix:
                return [MagicMock() for _ in range(5)]
            elif "/audio/" in prefix:
                return [MagicMock() for _ in range(50)]
            return []

        mock_minio_client.list_objects.side_effect = list_objects_side_effect
        # stat_object succeeds for vocabulary and metadata files
        mock_minio_client.stat_object.return_value = MagicMock()

        manager = AIDataCleanupManager(settings=mock_settings)
        counts = manager.get_cleanup_stats("pub", "book", "name")

        assert counts["text"] == 10
        assert counts["modules"] == 5
        assert counts["audio"] == 50
        assert counts["vocabulary"] == 1
        assert counts["metadata"] == 1
        # Total includes dirs + vocabulary + metadata
        assert counts["total"] == 67

    @patch("app.services.ai_data.cleanup.get_minio_client")
    def test_cleanup_handles_errors(self, mock_get_client, mock_settings, mock_minio_client):
        """Test cleanup handles individual file deletion errors."""
        mock_get_client.return_value = mock_minio_client

        mock_obj1 = MagicMock()
        mock_obj1.object_name = "pub/books/book/name/ai-data/text/page_001.txt"
        mock_obj2 = MagicMock()
        mock_obj2.object_name = "pub/books/book/name/ai-data/text/page_002.txt"

        mock_minio_client.list_objects.return_value = [mock_obj1, mock_obj2]

        # First delete succeeds, second fails
        mock_minio_client.remove_object.side_effect = [
            None,
            S3Error(
                code="AccessDenied",
                message="Access denied",
                resource="test",
                request_id="123",
                host_id="host",
                response=MagicMock(),
            ),
        ]

        manager = AIDataCleanupManager(settings=mock_settings)
        stats = manager.cleanup_all("pub", "book", "name")

        assert stats.total_deleted == 1
        assert len(stats.errors) == 1


# =============================================================================
# Test Provider Info Population
# =============================================================================


class TestProviderInfo:
    """Tests for provider info population from settings."""

    @patch("app.services.ai_data.service.get_minio_client")
    def test_provider_info_populated(self, mock_get_client):
        """Test that provider info is populated from settings."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        settings = MagicMock()
        settings.minio_publishers_bucket = "publishers"
        settings.llm_primary_provider = "gemini"
        settings.tts_primary_provider = "azure"

        service = AIDataMetadataService(settings=settings)
        metadata = service.create_metadata("book", "pub", "name")

        assert metadata.llm_provider == "gemini"
        assert metadata.tts_provider == "azure"
