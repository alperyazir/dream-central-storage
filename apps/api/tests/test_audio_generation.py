"""Tests for the audio generation service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.audio_generation.models import (
    AudioFile,
    AudioGenerationError,
    BookAudioResult,
    NoVocabularyFoundError,
    StorageError,
    TTSError,
    WordAudioResult,
)
from app.services.audio_generation.service import AudioGenerationService
from app.services.audio_generation.storage import AudioStorage


# =============================================================================
# Test Data Models
# =============================================================================


class TestAudioFile:
    """Tests for AudioFile dataclass."""

    def test_create_audio_file(self):
        """Test creating an audio file."""
        audio_file = AudioFile(
            word_id="beautiful",
            word="beautiful",
            language="en",
            file_path="audio/vocabulary/en/beautiful.mp3",
            duration_ms=500,
        )
        assert audio_file.word_id == "beautiful"
        assert audio_file.language == "en"
        assert audio_file.file_path == "audio/vocabulary/en/beautiful.mp3"
        assert audio_file.duration_ms == 500
        assert audio_file.generated_at is not None

    def test_to_dict(self):
        """Test converting audio file to dictionary."""
        audio_file = AudioFile(
            word_id="hello",
            word="hello",
            language="en",
            file_path="audio/vocabulary/en/hello.mp3",
            duration_ms=300,
        )
        d = audio_file.to_dict()
        assert d["word_id"] == "hello"
        assert d["word"] == "hello"
        assert d["language"] == "en"
        assert d["file_path"] == "audio/vocabulary/en/hello.mp3"
        assert d["duration_ms"] == 300
        assert "generated_at" in d

    def test_from_dict(self):
        """Test creating audio file from dictionary."""
        data = {
            "word_id": "test",
            "word": "test",
            "language": "en",
            "file_path": "audio/vocabulary/en/test.mp3",
            "duration_ms": 400,
            "generated_at": "2024-01-15T10:30:00+00:00",
        }
        audio_file = AudioFile.from_dict(data)
        assert audio_file.word_id == "test"
        assert audio_file.language == "en"
        assert audio_file.duration_ms == 400

    def test_from_dict_with_missing_fields(self):
        """Test creating audio file from partial dictionary."""
        data = {"word_id": "minimal", "word": "minimal"}
        audio_file = AudioFile.from_dict(data)
        assert audio_file.word_id == "minimal"
        assert audio_file.language == ""
        assert audio_file.duration_ms is None


class TestWordAudioResult:
    """Tests for WordAudioResult dataclass."""

    def test_create_successful_result(self):
        """Test creating a successful word audio result."""
        audio_file = AudioFile(
            word_id="hello",
            word="hello",
            language="en",
            file_path="audio/vocabulary/en/hello.mp3",
        )
        result = WordAudioResult(
            word_id="hello",
            word="hello",
            language="en",
            success=True,
            audio_file=audio_file,
        )
        assert result.success is True
        assert result.audio_file is not None
        assert result.error_message == ""

    def test_create_failed_result(self):
        """Test creating a failed word audio result."""
        result = WordAudioResult(
            word_id="test",
            word="test",
            language="en",
            success=False,
            error_message="TTS provider error",
        )
        assert result.success is False
        assert result.audio_file is None
        assert result.error_message == "TTS provider error"

    def test_to_dict(self):
        """Test converting word audio result to dictionary."""
        result = WordAudioResult(
            word_id="test",
            word="test",
            language="en",
            success=True,
        )
        d = result.to_dict()
        assert d["word_id"] == "test"
        assert d["success"] is True
        assert d["audio_file"] is None


class TestBookAudioResult:
    """Tests for BookAudioResult dataclass."""

    def test_create_book_audio_result(self):
        """Test creating a book audio result."""
        word_results = [
            WordAudioResult(word_id="hello", word="hello", language="en", success=True),
            WordAudioResult(word_id="world", word="world", language="en", success=True),
        ]
        result = BookAudioResult(
            book_id="book-123",
            publisher_id="pub-456",
            book_name="Test Book",
            language="en",
            translation_language="tr",
            total_words=10,
            word_results=word_results,
        )
        assert result.book_id == "book-123"
        assert result.language == "en"
        assert result.generated_count == 2
        assert result.failed_count == 0

    def test_aggregate_counts(self):
        """Test that aggregate counts are calculated correctly."""
        word_results = [
            WordAudioResult(word_id="a", word="a", language="en", success=True),
            WordAudioResult(word_id="b", word="b", language="en", success=True),
            WordAudioResult(word_id="c", word="c", language="en", success=False),
        ]
        result = BookAudioResult(
            book_id="book-123",
            publisher_id="pub-456",
            book_name="Test",
            word_results=word_results,
        )
        assert result.generated_count == 2
        assert result.failed_count == 1

    def test_to_dict(self):
        """Test to_dict produces summary format."""
        result = BookAudioResult(
            book_id="book-123",
            publisher_id="pub-456",
            book_name="Test",
            language="en",
            translation_language="tr",
            total_words=5,
        )
        d = result.to_dict()
        assert d["book_id"] == "book-123"
        assert d["language"] == "en"
        assert d["total_words"] == 5
        assert "generated_at" in d


# =============================================================================
# Test Exceptions
# =============================================================================


class TestExceptions:
    """Tests for exception classes."""

    def test_audio_generation_error(self):
        """Test base audio generation error."""
        error = AudioGenerationError(
            message="Test error",
            book_id="book-123",
            details={"key": "value"},
        )
        assert "book-123" in str(error)
        assert "Test error" in str(error)
        assert error.details == {"key": "value"}

    def test_tts_error(self):
        """Test TTS error."""
        error = TTSError(
            book_id="book-123",
            word="hello",
            language="en",
            reason="Provider timeout",
            provider="edge",
        )
        assert error.word == "hello"
        assert error.language == "en"
        assert error.reason == "Provider timeout"
        assert error.provider == "edge"

    def test_storage_error(self):
        """Test storage error."""
        error = StorageError(
            book_id="book-123",
            operation="save",
            path="/some/path",
            reason="Permission denied",
        )
        assert error.operation == "save"
        assert error.path == "/some/path"
        assert error.reason == "Permission denied"

    def test_no_vocabulary_found_error(self):
        """Test no vocabulary found error."""
        error = NoVocabularyFoundError(
            book_id="book-123",
            path="/some/path/vocabulary.json",
        )
        assert error.path == "/some/path/vocabulary.json"


# =============================================================================
# Test Audio Generation Service
# =============================================================================


class TestAudioGenerationService:
    """Tests for AudioGenerationService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.audio_generation_concurrency = 5
        settings.audio_generation_languages = "en,tr"
        settings.audio_retry_failed = True
        settings.tts_batch_concurrency = 5
        return settings

    @pytest.fixture
    def mock_tts_service(self):
        """Create mock TTS service."""
        tts_service = MagicMock()
        tts_service.synthesize_text = AsyncMock()
        tts_service.synthesize_batch = AsyncMock()
        return tts_service

    @pytest.fixture
    def service(self, mock_settings, mock_tts_service):
        """Create service with mocked dependencies."""
        return AudioGenerationService(
            settings=mock_settings,
            tts_service=mock_tts_service,
        )

    @pytest.mark.asyncio
    async def test_generate_word_audio_success(self, service, mock_tts_service):
        """Test successful audio generation for single word."""
        mock_response = MagicMock()
        mock_response.audio_data = b"fake audio data"
        mock_response.duration_ms = 500
        mock_tts_service.synthesize_text.return_value = mock_response

        result = await service.generate_word_audio(
            word="hello",
            word_id="hello",
            language="en",
            book_id="book-123",
        )

        assert result.success is True
        assert result.word_id == "hello"
        assert result.audio_file is not None
        assert result.audio_file.file_path == "audio/vocabulary/en/hello.mp3"

    @pytest.mark.asyncio
    async def test_generate_word_audio_failure(self, service, mock_tts_service):
        """Test handling of TTS failure for single word."""
        from app.services.tts import TTSProviderError

        mock_tts_service.synthesize_text.side_effect = TTSProviderError(
            "Provider error", "edge"
        )

        result = await service.generate_word_audio(
            word="hello",
            word_id="hello",
            language="en",
            book_id="book-123",
        )

        assert result.success is False
        assert result.audio_file is None
        assert "Provider error" in result.error_message

    @pytest.mark.asyncio
    async def test_generate_vocabulary_audio_success(self, service, mock_tts_service):
        """Test successful audio generation for vocabulary."""
        mock_response1 = MagicMock()
        mock_response1.audio_data = b"hello audio"
        mock_response1.duration_ms = 300

        mock_response2 = MagicMock()
        mock_response2.audio_data = b"merhaba audio"
        mock_response2.duration_ms = 350

        mock_batch_result = MagicMock()
        mock_batch_result.results = [mock_response1, mock_response2]
        mock_batch_result.errors = []
        mock_tts_service.synthesize_batch.return_value = mock_batch_result

        vocabulary = [
            {"id": "hello", "word": "hello", "translation": "merhaba"},
        ]

        result, audio_data = await service.generate_vocabulary_audio(
            vocabulary=vocabulary,
            book_id="book-123",
            publisher_id="pub-456",
            book_name="Test Book",
            language="en",
            translation_language="tr",
        )

        assert result.book_id == "book-123"
        assert result.total_words == 1
        assert len(audio_data) == 2  # word + translation
        assert "audio/vocabulary/en/hello.mp3" in audio_data
        assert "audio/vocabulary/tr/merhaba.mp3" in audio_data

    @pytest.mark.asyncio
    async def test_generate_vocabulary_audio_empty(self, service):
        """Test handling of empty vocabulary."""
        result, audio_data = await service.generate_vocabulary_audio(
            vocabulary=[],
            book_id="book-123",
            publisher_id="pub-456",
            book_name="Test Book",
        )

        assert result.total_words == 0
        assert len(audio_data) == 0

    @pytest.mark.asyncio
    async def test_generate_vocabulary_audio_partial_failure(
        self, service, mock_tts_service
    ):
        """Test handling of partial failures in batch."""
        mock_response = MagicMock()
        mock_response.audio_data = b"hello audio"
        mock_response.duration_ms = 300

        mock_batch_result = MagicMock()
        mock_batch_result.results = [mock_response, None]  # Second item failed
        mock_batch_result.errors = [(1, "TTS timeout")]
        mock_tts_service.synthesize_batch.return_value = mock_batch_result

        vocabulary = [
            {"id": "hello", "word": "hello", "translation": "merhaba"},
        ]

        result, audio_data = await service.generate_vocabulary_audio(
            vocabulary=vocabulary,
            book_id="book-123",
            publisher_id="pub-456",
            book_name="Test Book",
        )

        assert result.generated_count == 1
        assert result.failed_count == 1
        assert len(audio_data) == 1

    @pytest.mark.asyncio
    async def test_generate_vocabulary_audio_with_progress(
        self, service, mock_tts_service
    ):
        """Test audio generation with progress callback."""
        mock_response = MagicMock()
        mock_response.audio_data = b"audio"
        mock_response.duration_ms = 300

        mock_batch_result = MagicMock()
        mock_batch_result.results = [mock_response, mock_response]
        mock_batch_result.errors = []
        mock_tts_service.synthesize_batch.return_value = mock_batch_result

        progress_calls = []

        def progress_callback(current: int, total: int) -> None:
            progress_calls.append((current, total))

        vocabulary = [
            {"id": "hello", "word": "hello", "translation": "merhaba"},
        ]

        await service.generate_vocabulary_audio(
            vocabulary=vocabulary,
            book_id="book-123",
            publisher_id="pub-456",
            book_name="Test Book",
            progress_callback=progress_callback,
        )

        assert len(progress_calls) == 2  # word + translation
        assert progress_calls[-1][0] == 2  # Final progress

    @pytest.mark.asyncio
    async def test_generate_vocabulary_audio_without_translation(
        self, service, mock_tts_service
    ):
        """Test audio generation for word without translation."""
        mock_response = MagicMock()
        mock_response.audio_data = b"audio"
        mock_response.duration_ms = 300

        mock_batch_result = MagicMock()
        mock_batch_result.results = [mock_response]
        mock_batch_result.errors = []
        mock_tts_service.synthesize_batch.return_value = mock_batch_result

        vocabulary = [
            {"id": "hello", "word": "hello", "translation": ""},  # No translation
        ]

        result, audio_data = await service.generate_vocabulary_audio(
            vocabulary=vocabulary,
            book_id="book-123",
            publisher_id="pub-456",
            book_name="Test Book",
        )

        # Should only generate word audio, not translation
        assert len(audio_data) == 1
        assert "audio/vocabulary/en/hello.mp3" in audio_data


# =============================================================================
# Test Audio Storage
# =============================================================================


class TestAudioStorage:
    """Tests for AudioStorage."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.minio_publishers_bucket = "publishers"
        return settings

    @pytest.fixture
    def storage(self, mock_settings):
        """Create storage with mocked settings."""
        return AudioStorage(settings=mock_settings)

    def test_build_vocabulary_path(self, storage):
        """Test building vocabulary.json path."""
        path = storage._build_vocabulary_path(
            publisher_id="pub-123",
            book_id="book-456",
            book_name="Test Book",
        )
        assert path == "pub-123/books/book-456/Test Book/ai-data/vocabulary.json"

    def test_build_audio_path(self, storage):
        """Test building audio file path."""
        path = storage._build_audio_path(
            publisher_id="pub-123",
            book_id="book-456",
            book_name="Test Book",
            language="en",
            word_id="hello",
        )
        assert (
            path
            == "pub-123/books/book-456/Test Book/ai-data/audio/vocabulary/en/hello.mp3"
        )

    def test_build_audio_prefix(self, storage):
        """Test building audio directory prefix."""
        prefix = storage._build_audio_prefix(
            publisher_id="pub-123",
            book_id="book-456",
            book_name="Test Book",
        )
        assert (
            prefix == "pub-123/books/book-456/Test Book/ai-data/audio/vocabulary/"
        )

    @patch("app.services.audio_generation.storage.get_minio_client")
    def test_load_vocabulary_not_found(self, mock_get_client, storage):
        """Test loading vocabulary when file doesn't exist."""
        from minio.error import S3Error

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_object.side_effect = S3Error(
            "NoSuchKey", "Not found", "", "", "", ""
        )

        with pytest.raises(NoVocabularyFoundError):
            storage.load_vocabulary(
                publisher_id="pub-123",
                book_id="book-456",
                book_name="Test Book",
            )

    @patch("app.services.audio_generation.storage.get_minio_client")
    def test_load_vocabulary_success(self, mock_get_client, storage):
        """Test loading vocabulary successfully."""
        vocabulary_data = {
            "language": "en",
            "translation_language": "tr",
            "total_words": 1,
            "words": [{"id": "test", "word": "test", "audio": {}}],
        }

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(vocabulary_data).encode("utf-8")
        mock_client.get_object.return_value = mock_response

        result = storage.load_vocabulary(
            publisher_id="pub-123",
            book_id="book-456",
            book_name="Test Book",
        )

        assert result is not None
        assert result["language"] == "en"
        assert result["total_words"] == 1

    @patch("app.services.audio_generation.storage.get_minio_client")
    def test_save_audio_file(self, mock_get_client, storage):
        """Test saving a single audio file."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        audio_file = AudioFile(
            word_id="hello",
            word="hello",
            language="en",
            file_path="audio/vocabulary/en/hello.mp3",
        )

        path = storage.save_audio_file(
            publisher_id="pub-123",
            book_id="book-456",
            book_name="Test Book",
            audio_file=audio_file,
            audio_data=b"fake audio data",
        )

        assert "hello.mp3" in path
        mock_client.put_object.assert_called_once()

    @patch("app.services.audio_generation.storage.get_minio_client")
    def test_save_audio_file_error(self, mock_get_client, storage):
        """Test handling of save error."""
        from minio.error import S3Error

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.put_object.side_effect = S3Error(
            "AccessDenied", "Access denied", "", "", "", ""
        )

        audio_file = AudioFile(
            word_id="hello",
            word="hello",
            language="en",
            file_path="audio/vocabulary/en/hello.mp3",
        )

        with pytest.raises(StorageError) as exc_info:
            storage.save_audio_file(
                publisher_id="pub-123",
                book_id="book-456",
                book_name="Test Book",
                audio_file=audio_file,
                audio_data=b"fake audio data",
            )

        assert exc_info.value.operation == "save"

    @patch("app.services.audio_generation.storage.get_minio_client")
    def test_save_all_audio(self, mock_get_client, storage):
        """Test saving all audio files."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        audio_files = [
            AudioFile(
                word_id="hello",
                word="hello",
                language="en",
                file_path="audio/vocabulary/en/hello.mp3",
            ),
            AudioFile(
                word_id="merhaba",
                word="merhaba",
                language="tr",
                file_path="audio/vocabulary/tr/merhaba.mp3",
            ),
        ]

        audio_data = {
            "audio/vocabulary/en/hello.mp3": b"hello audio",
            "audio/vocabulary/tr/merhaba.mp3": b"merhaba audio",
        }

        result = storage.save_all_audio(
            publisher_id="pub-123",
            book_id="book-456",
            book_name="Test Book",
            audio_files=audio_files,
            audio_data=audio_data,
        )

        assert result["saved"] == 2
        assert result["failed"] == 0
        assert mock_client.put_object.call_count == 2

    @patch("app.services.audio_generation.storage.get_minio_client")
    def test_update_vocabulary_audio_paths(self, mock_get_client, storage):
        """Test updating vocabulary.json with audio paths."""
        vocabulary_data = {
            "language": "en",
            "translation_language": "tr",
            "total_words": 1,
            "words": [
                {
                    "id": "hello",
                    "word": "hello",
                    "translation": "merhaba",
                    "audio": {},
                }
            ],
        }

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(vocabulary_data).encode("utf-8")
        mock_client.get_object.return_value = mock_response

        audio_files = [
            AudioFile(
                word_id="hello",
                word="hello",
                language="en",
                file_path="audio/vocabulary/en/hello.mp3",
            ),
            AudioFile(
                word_id="merhaba",
                word="merhaba",
                language="tr",
                file_path="audio/vocabulary/tr/merhaba.mp3",
            ),
        ]

        path = storage.update_vocabulary_audio_paths(
            publisher_id="pub-123",
            book_id="book-456",
            book_name="Test Book",
            audio_files=audio_files,
        )

        assert "vocabulary.json" in path
        mock_client.put_object.assert_called_once()

        # Verify the saved data contains audio paths
        call_args = mock_client.put_object.call_args
        saved_data = call_args[0][2].read()  # Get the BytesIO data
        saved_json = json.loads(saved_data.decode("utf-8"))
        assert saved_json["words"][0]["audio"]["word"] == "audio/vocabulary/en/hello.mp3"

    @patch("app.services.audio_generation.storage.get_minio_client")
    def test_cleanup_audio_directory(self, mock_get_client, storage):
        """Test cleaning up audio directory."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock list_objects to return some audio files
        mock_obj1 = MagicMock()
        mock_obj1.object_name = "pub/books/book/Test/ai-data/audio/vocabulary/en/word1.mp3"
        mock_obj2 = MagicMock()
        mock_obj2.object_name = "pub/books/book/Test/ai-data/audio/vocabulary/tr/word1.mp3"
        mock_client.list_objects.return_value = [mock_obj1, mock_obj2]

        deleted_count = storage.cleanup_audio_directory(
            publisher_id="pub-123",
            book_id="book-456",
            book_name="Test Book",
        )

        assert deleted_count == 2
        assert mock_client.remove_object.call_count == 2

    def test_slugify(self, storage):
        """Test slugify helper method."""
        assert storage._slugify("Hello World") == "hello_world"
        assert storage._slugify("can't stop!") == "can_t_stop"
        assert storage._slugify("über") == "ber"  # Non-ASCII removed
        assert storage._slugify("  test  ") == "test"


# =============================================================================
# Test Configuration Integration
# =============================================================================


class TestConfigurationIntegration:
    """Tests for configuration settings."""

    def test_audio_generation_settings_exist(self):
        """Test that audio generation settings are defined in config."""
        from app.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "audio_generation_concurrency")
        assert hasattr(settings, "audio_generation_languages")
        assert hasattr(settings, "audio_retry_failed")

    def test_audio_generation_default_values(self):
        """Test default values for audio generation settings."""
        from app.core.config import Settings

        settings = Settings()
        assert settings.audio_generation_concurrency == 5
        assert settings.audio_generation_languages == "en,tr"
        assert settings.audio_retry_failed is True
