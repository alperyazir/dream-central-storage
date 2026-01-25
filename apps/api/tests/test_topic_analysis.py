"""Tests for the topic analysis service."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.topic_analysis.models import (
    BookAnalysisResult,
    CEFRLevel,
    DetectedLanguage,
    InvalidLLMResponseError,
    LLMAnalysisError,
    ModuleAnalysisResult,
    NoModulesFoundError,
    TargetSkill,
    TopicAnalysisError,
    TopicResult,
)
from app.services.topic_analysis.prompts import (
    SYSTEM_PROMPT,
    build_difficulty_detection_prompt,
    build_grammar_extraction_prompt,
    build_language_detection_prompt,
    build_simple_topic_prompt,
    build_topic_extraction_prompt,
)
from app.services.topic_analysis.service import TopicAnalysisService
from app.services.topic_analysis.storage import TopicStorage


# =============================================================================
# Test Data Models
# =============================================================================


class TestTopicResult:
    """Tests for TopicResult dataclass."""

    def test_create_topic_result(self):
        """Test creating a topic result."""
        result = TopicResult(
            topics=["greetings", "introductions"],
            grammar_points=["present simple"],
            difficulty="A1",
            language="en",
            target_skills=["reading", "listening"],
        )
        assert result.topics == ["greetings", "introductions"]
        assert result.grammar_points == ["present simple"]
        assert result.difficulty == "A1"
        assert result.language == "en"
        assert result.target_skills == ["reading", "listening"]

    def test_empty_topic_result(self):
        """Test creating an empty topic result."""
        result = TopicResult.empty()
        assert result.topics == []
        assert result.grammar_points == []
        assert result.difficulty == ""
        assert result.language == ""
        assert result.target_skills == []

    def test_to_dict(self):
        """Test converting topic result to dictionary."""
        result = TopicResult(
            topics=["vocabulary"],
            grammar_points=["articles"],
            difficulty="B1",
            language="tr",
            target_skills=["speaking"],
        )
        d = result.to_dict()
        assert d["topics"] == ["vocabulary"]
        assert d["grammar_points"] == ["articles"]
        assert d["difficulty"] == "B1"
        assert d["language"] == "tr"
        assert d["target_skills"] == ["speaking"]

    def test_from_dict(self):
        """Test creating topic result from dictionary."""
        data = {
            "topics": ["colors", "numbers"],
            "grammar_points": ["plurals"],
            "difficulty": "A2",
            "language": "en",
            "target_skills": ["writing"],
        }
        result = TopicResult.from_dict(data)
        assert result.topics == ["colors", "numbers"]
        assert result.grammar_points == ["plurals"]
        assert result.difficulty == "A2"
        assert result.language == "en"

    def test_from_dict_with_missing_fields(self):
        """Test creating topic result from partial dictionary."""
        data = {"topics": ["test"]}
        result = TopicResult.from_dict(data)
        assert result.topics == ["test"]
        assert result.grammar_points == []
        assert result.difficulty == ""
        assert result.language == ""


class TestModuleAnalysisResult:
    """Tests for ModuleAnalysisResult dataclass."""

    def test_create_module_analysis_result(self):
        """Test creating a module analysis result."""
        topic_result = TopicResult(
            topics=["greetings"],
            difficulty="A1",
            language="en",
        )
        result = ModuleAnalysisResult(
            module_id=1,
            module_title="Unit 1",
            topic_result=topic_result,
            llm_provider="deepseek",
            tokens_used=150,
            success=True,
        )
        assert result.module_id == 1
        assert result.module_title == "Unit 1"
        assert result.topic_result.topics == ["greetings"]
        assert result.llm_provider == "deepseek"
        assert result.success is True

    def test_failed_module_analysis_result(self):
        """Test creating a failed module analysis result."""
        result = ModuleAnalysisResult(
            module_id=2,
            module_title="Unit 2",
            topic_result=TopicResult.empty(),
            success=False,
            error_message="LLM timeout",
        )
        assert result.module_id == 2
        assert result.success is False
        assert result.error_message == "LLM timeout"

    def test_to_dict(self):
        """Test converting module analysis result to dictionary."""
        result = ModuleAnalysisResult(
            module_id=1,
            module_title="Test",
            topic_result=TopicResult(topics=["test"]),
            success=True,
        )
        d = result.to_dict()
        assert d["module_id"] == 1
        assert d["module_title"] == "Test"
        assert d["success"] is True
        assert "topic_result" in d


class TestBookAnalysisResult:
    """Tests for BookAnalysisResult dataclass."""

    def test_create_book_analysis_result(self):
        """Test creating a book analysis result."""
        module_results = [
            ModuleAnalysisResult(
                module_id=1,
                module_title="Unit 1",
                topic_result=TopicResult(
                    topics=["greetings"],
                    difficulty="A1",
                    language="en",
                ),
                success=True,
            ),
            ModuleAnalysisResult(
                module_id=2,
                module_title="Unit 2",
                topic_result=TopicResult(
                    topics=["family"],
                    difficulty="A2",
                    language="en",
                ),
                success=True,
            ),
        ]
        result = BookAnalysisResult(
            book_id="book-123",
            publisher_id="pub-1",
            book_name="English101",
            module_results=module_results,
        )
        assert result.book_id == "book-123"
        assert result.success_count == 2
        assert result.failure_count == 0
        assert result.primary_language == "en"
        assert "A1" in result.difficulty_range
        assert "A2" in result.difficulty_range

    def test_book_with_failures(self):
        """Test book analysis with some failed modules."""
        module_results = [
            ModuleAnalysisResult(
                module_id=1,
                module_title="Unit 1",
                topic_result=TopicResult(topics=["test"], language="en", difficulty="A1"),
                success=True,
            ),
            ModuleAnalysisResult(
                module_id=2,
                module_title="Unit 2",
                topic_result=TopicResult.empty(),
                success=False,
                error_message="Error",
            ),
        ]
        result = BookAnalysisResult(
            book_id="book-123",
            publisher_id="pub-1",
            book_name="Test",
            module_results=module_results,
        )
        assert result.success_count == 1
        assert result.failure_count == 1

    def test_to_dict(self):
        """Test converting book analysis result to dictionary."""
        result = BookAnalysisResult(
            book_id="book-123",
            publisher_id="pub-1",
            book_name="Test",
            module_results=[],
        )
        d = result.to_dict()
        assert d["book_id"] == "book-123"
        assert d["publisher_id"] == "pub-1"
        assert d["module_count"] == 0


class TestExceptions:
    """Tests for exception classes."""

    def test_topic_analysis_error(self):
        """Test base TopicAnalysisError."""
        error = TopicAnalysisError(
            message="Test error",
            book_id="book-123",
            details={"key": "value"},
        )
        assert error.message == "Test error"
        assert error.book_id == "book-123"
        assert error.details == {"key": "value"}
        assert "[book-123]" in str(error)

    def test_llm_analysis_error(self):
        """Test LLMAnalysisError."""
        error = LLMAnalysisError(
            book_id="book-123",
            module_id=5,
            reason="Timeout",
            provider="deepseek",
        )
        assert error.module_id == 5
        assert error.reason == "Timeout"
        assert error.provider == "deepseek"

    def test_no_modules_found_error(self):
        """Test NoModulesFoundError."""
        error = NoModulesFoundError(
            book_id="book-123",
            path="/path/to/modules",
        )
        assert error.path == "/path/to/modules"

    def test_invalid_llm_response_error(self):
        """Test InvalidLLMResponseError."""
        error = InvalidLLMResponseError(
            book_id="book-123",
            module_id=1,
            response="invalid json",
            parse_error="Expected ':'",
        )
        assert error.module_id == 1
        assert error.parse_error == "Expected ':'"


# =============================================================================
# Test Prompts
# =============================================================================


class TestPrompts:
    """Tests for LLM prompt templates."""

    def test_build_topic_extraction_prompt(self):
        """Test building topic extraction prompt."""
        text = "This is module text about greetings."
        prompt = build_topic_extraction_prompt(text)
        assert "greetings" in prompt
        assert "topics" in prompt
        assert "difficulty" in prompt
        assert "JSON" in prompt

    def test_build_topic_extraction_prompt_truncation(self):
        """Test prompt truncation for long text."""
        long_text = "word " * 5000  # Very long text
        prompt = build_topic_extraction_prompt(long_text, max_length=1000)
        assert len(prompt) < len(long_text) + 1000
        assert "[Text truncated...]" in prompt

    def test_build_simple_topic_prompt(self):
        """Test building simple topic prompt."""
        text = "Simple test text"
        prompt = build_simple_topic_prompt(text)
        assert "Simple test text" in prompt
        assert "topics" in prompt

    def test_build_language_detection_prompt(self):
        """Test building language detection prompt."""
        text = "Hello world"
        prompt = build_language_detection_prompt(text)
        assert "Hello world" in prompt
        assert "language" in prompt
        assert "bilingual" in prompt

    def test_build_difficulty_detection_prompt(self):
        """Test building difficulty detection prompt."""
        text = "Educational content here"
        prompt = build_difficulty_detection_prompt(text)
        assert "Educational content here" in prompt
        assert "CEFR" in prompt
        assert "A1" in prompt

    def test_build_grammar_extraction_prompt(self):
        """Test building grammar extraction prompt."""
        text = "Learn the present tense"
        prompt = build_grammar_extraction_prompt(text)
        assert "present tense" in prompt
        assert "grammar" in prompt

    def test_system_prompt_exists(self):
        """Test that system prompt is defined."""
        assert SYSTEM_PROMPT
        assert "educational" in SYSTEM_PROMPT.lower()
        assert "JSON" in SYSTEM_PROMPT


# =============================================================================
# Test Service
# =============================================================================


class TestTopicAnalysisService:
    """Tests for TopicAnalysisService."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.topic_analysis_max_topics = 5
        settings.topic_analysis_max_grammar_points = 10
        settings.topic_analysis_temperature = 0.3
        settings.topic_analysis_max_text_length = 8000
        return settings

    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service."""
        llm = AsyncMock()
        llm.simple_completion = AsyncMock()
        llm.primary_provider = MagicMock()
        llm.primary_provider.provider_name = "deepseek"
        return llm

    @pytest.fixture
    def service(self, mock_settings, mock_llm_service):
        """Create topic analysis service with mocks."""
        return TopicAnalysisService(
            settings=mock_settings,
            llm_service=mock_llm_service,
        )

    @pytest.mark.asyncio
    async def test_analyze_module_success(self, service, mock_llm_service):
        """Test successful module analysis."""
        mock_llm_service.simple_completion.return_value = json.dumps({
            "topics": ["greetings", "introductions"],
            "grammar_points": ["present simple"],
            "difficulty": "A1",
            "language": "en",
            "target_skills": ["reading", "listening"],
        })

        # Text must be > 50 chars to trigger LLM analysis
        module_text = """
        Hello, my name is John. Nice to meet you.
        This is a lesson about greetings and introductions.
        We will learn how to say hello and introduce ourselves.
        """

        result = await service.analyze_module(
            module_id=1,
            module_title="Unit 1: Greetings",
            module_text=module_text,
            book_id="book-123",
        )

        assert result.success is True
        assert result.module_id == 1
        assert "greetings" in result.topic_result.topics
        assert result.topic_result.difficulty == "A1"
        assert result.topic_result.language == "en"

    @pytest.mark.asyncio
    async def test_analyze_module_with_json_in_markdown(self, service, mock_llm_service):
        """Test parsing JSON wrapped in markdown code blocks."""
        mock_llm_service.simple_completion.return_value = """
Here is the analysis:

```json
{
    "topics": ["family", "relatives"],
    "grammar_points": [],
    "difficulty": "A2",
    "language": "en",
    "target_skills": ["reading"]
}
```
"""
        # Text must be > 50 chars to trigger LLM analysis
        module_text = """
        This chapter is about family members and relatives.
        Learn the names of your mother, father, sister, and brother.
        """

        result = await service.analyze_module(
            module_id=1,
            module_title="Unit 2",
            module_text=module_text,
            book_id="book-123",
        )

        assert result.success is True
        assert "family" in result.topic_result.topics
        assert result.topic_result.difficulty == "A2"

    @pytest.mark.asyncio
    async def test_analyze_module_empty_text(self, service):
        """Test analyzing module with empty text."""
        result = await service.analyze_module(
            module_id=1,
            module_title="Empty",
            module_text="",
            book_id="book-123",
        )

        assert result.success is True
        assert result.topic_result.topics == []
        assert "Insufficient text" in result.error_message

    @pytest.mark.asyncio
    async def test_analyze_module_minimal_text(self, service):
        """Test analyzing module with very short text."""
        result = await service.analyze_module(
            module_id=1,
            module_title="Short",
            module_text="Hi",  # Less than 50 chars
            book_id="book-123",
        )

        assert result.success is True
        assert "Insufficient text" in result.error_message

    @pytest.mark.asyncio
    async def test_analyze_module_invalid_json_response(self, service, mock_llm_service):
        """Test handling invalid JSON response with fallback."""
        # First call returns invalid JSON, second returns valid
        mock_llm_service.simple_completion.side_effect = [
            "This is not valid JSON at all - just random text response",
            json.dumps({
                "topics": ["test"],
                "difficulty": "B1",
                "language": "en",
            }),
        ]

        # Text must be > 50 chars to trigger LLM analysis
        module_text = """
        Some educational content here for testing the JSON parsing.
        This lesson covers various topics in detail with examples.
        """

        result = await service.analyze_module(
            module_id=1,
            module_title="Test",
            module_text=module_text,
            book_id="book-123",
        )

        # Should have tried fallback and succeeded
        assert mock_llm_service.simple_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_analyze_module_llm_error(self, service, mock_llm_service):
        """Test handling LLM provider error."""
        from app.services.llm import LLMProviderError

        mock_llm_service.simple_completion.side_effect = LLMProviderError(
            message="API Error",
            provider="deepseek",
        )

        # Text must be > 50 chars to trigger LLM analysis
        module_text = """
        Content for testing the error handling functionality.
        This educational text covers important topics for students.
        """

        result = await service.analyze_module(
            module_id=1,
            module_title="Test",
            module_text=module_text,
            book_id="book-123",
        )

        assert result.success is False
        assert "LLM provider error" in result.error_message

    @pytest.mark.asyncio
    async def test_analyze_module_normalizes_difficulty(self, service, mock_llm_service):
        """Test that difficulty is normalized to uppercase."""
        mock_llm_service.simple_completion.return_value = json.dumps({
            "topics": ["test"],
            "difficulty": "b2",  # lowercase
            "language": "en",
        })

        # Text must be > 50 chars to trigger LLM analysis
        module_text = """
        Content with intermediate difficulty level for language learners.
        This material is designed for upper-intermediate students.
        """

        result = await service.analyze_module(
            module_id=1,
            module_title="Test",
            module_text=module_text,
            book_id="book-123",
        )

        assert result.topic_result.difficulty == "B2"

    @pytest.mark.asyncio
    async def test_analyze_module_normalizes_language(self, service, mock_llm_service):
        """Test that language is normalized to lowercase."""
        mock_llm_service.simple_completion.return_value = json.dumps({
            "topics": ["test"],
            "difficulty": "A1",
            "language": "EN",  # uppercase
        })

        # Text must be > 50 chars to trigger LLM analysis
        module_text = """
        Some content written in English language for testing purposes.
        This lesson teaches basic vocabulary and simple sentences.
        """

        result = await service.analyze_module(
            module_id=1,
            module_title="Test",
            module_text=module_text,
            book_id="book-123",
        )

        assert result.topic_result.language == "en"

    @pytest.mark.asyncio
    async def test_analyze_module_invalid_difficulty_ignored(self, service, mock_llm_service):
        """Test that invalid difficulty levels are ignored."""
        mock_llm_service.simple_completion.return_value = json.dumps({
            "topics": ["test"],
            "difficulty": "X9",  # Invalid CEFR level
            "language": "en",
        })

        # Text must be > 50 chars to trigger LLM analysis
        module_text = """
        Content with unknown difficulty level that cannot be categorized.
        The LLM returned an invalid CEFR level in its response.
        """

        result = await service.analyze_module(
            module_id=1,
            module_title="Test",
            module_text=module_text,
            book_id="book-123",
        )

        assert result.topic_result.difficulty == ""

    @pytest.mark.asyncio
    async def test_analyze_module_limits_topics(self, service, mock_llm_service):
        """Test that topics are limited to max_topics setting."""
        mock_llm_service.simple_completion.return_value = json.dumps({
            "topics": ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"],
            "difficulty": "A1",
            "language": "en",
        })

        # Text must be > 50 chars to trigger LLM analysis
        module_text = """
        Content with many topics to extract from this educational material.
        The lesson covers multiple subjects and vocabulary areas.
        """

        result = await service.analyze_module(
            module_id=1,
            module_title="Test",
            module_text=module_text,
            book_id="book-123",
        )

        # max_topics is 5 in mock_settings
        assert len(result.topic_result.topics) <= 5

    @pytest.mark.asyncio
    async def test_analyze_book_success(self, service, mock_llm_service):
        """Test successful book analysis."""
        mock_llm_service.simple_completion.return_value = json.dumps({
            "topics": ["greetings"],
            "grammar_points": ["present simple"],
            "difficulty": "A1",
            "language": "en",
            "target_skills": ["reading"],
        })

        # Text must be > 50 chars to trigger LLM analysis
        modules = [
            {"module_id": 1, "title": "Unit 1", "text": "Hello world content here. This is an introduction to greetings and basic phrases."},
            {"module_id": 2, "title": "Unit 2", "text": "More educational content about family and relationships in English language."},
        ]

        result = await service.analyze_book(
            book_id="book-123",
            publisher_id="pub-1",
            book_name="TestBook",
            modules=modules,
        )

        assert result.book_id == "book-123"
        assert len(result.module_results) == 2
        assert result.success_count == 2
        assert result.primary_language == "en"

    @pytest.mark.asyncio
    async def test_analyze_book_no_modules(self, service):
        """Test analyzing book with no modules raises error."""
        with pytest.raises(NoModulesFoundError):
            await service.analyze_book(
                book_id="book-123",
                publisher_id="pub-1",
                book_name="Empty",
                modules=[],
            )

    @pytest.mark.asyncio
    async def test_analyze_book_progress_callback(self, service, mock_llm_service):
        """Test that progress callback is called."""
        mock_llm_service.simple_completion.return_value = json.dumps({
            "topics": ["test"],
            "difficulty": "A1",
            "language": "en",
        })

        progress_calls = []

        def progress_callback(current: int, total: int) -> None:
            progress_calls.append((current, total))

        # Text must be > 50 chars to trigger LLM analysis
        modules = [
            {"module_id": 1, "title": "Unit 1", "text": "Content one for the first module with enough text to process."},
            {"module_id": 2, "title": "Unit 2", "text": "Content two for the second module with sufficient length."},
            {"module_id": 3, "title": "Unit 3", "text": "Content three for the third module also long enough."},
        ]

        await service.analyze_book(
            book_id="book-123",
            publisher_id="pub-1",
            book_name="Test",
            modules=modules,
            progress_callback=progress_callback,
        )

        assert len(progress_calls) == 3
        assert progress_calls[0] == (1, 3)
        assert progress_calls[1] == (2, 3)
        assert progress_calls[2] == (3, 3)

    @pytest.mark.asyncio
    async def test_analyze_book_mixed_languages(self, service, mock_llm_service):
        """Test detecting primary language from mixed modules."""
        # Mock different languages for different modules
        mock_llm_service.simple_completion.side_effect = [
            json.dumps({"topics": ["t1"], "difficulty": "A1", "language": "en"}),
            json.dumps({"topics": ["t2"], "difficulty": "A1", "language": "en"}),
            json.dumps({"topics": ["t3"], "difficulty": "A1", "language": "tr"}),
        ]

        # Text must be > 50 chars to trigger LLM analysis
        modules = [
            {"module_id": 1, "title": "Unit 1", "text": "English content for the first unit with greetings and introductions."},
            {"module_id": 2, "title": "Unit 2", "text": "More English content covering family vocabulary and relationships."},
            {"module_id": 3, "title": "Unit 3", "text": "Turkish content about colors and numbers in a different language."},
        ]

        result = await service.analyze_book(
            book_id="book-123",
            publisher_id="pub-1",
            book_name="Mixed",
            modules=modules,
        )

        # Primary language should be the most common
        assert result.primary_language == "en"


# =============================================================================
# Test Storage
# =============================================================================


class TestTopicStorage:
    """Tests for TopicStorage."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.minio_publishers_bucket = "publishers"
        return settings

    @pytest.fixture
    def storage(self, mock_settings):
        """Create topic storage with mock settings."""
        return TopicStorage(settings=mock_settings)

    def test_build_module_path(self, storage):
        """Test building module file path."""
        path = storage._build_module_path("pub-1", "book-123", "TestBook", 1)
        # Note: book_id is not in the path, only publisher_id and book_name
        assert path == "pub-1/books/TestBook/ai-data/modules/module_1.json"

    def test_build_metadata_path(self, storage):
        """Test building metadata file path."""
        path = storage._build_metadata_path("pub-1", "book-123", "TestBook")
        # Note: book_id is not in the path, only publisher_id and book_name
        assert path == "pub-1/books/TestBook/ai-data/modules/topic_analysis_metadata.json"

    @patch("app.services.topic_analysis.storage.get_minio_client")
    def test_get_module_found(self, mock_get_client, storage):
        """Test getting an existing module."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        module_data = {"module_id": 1, "title": "Test", "text": "Content"}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(module_data).encode()
        mock_client.get_object.return_value = mock_response

        result = storage.get_module("pub-1", "book-123", "TestBook", 1)

        assert result is not None
        assert result["module_id"] == 1

    @patch("app.services.topic_analysis.storage.get_minio_client")
    def test_get_module_not_found(self, mock_get_client, storage):
        """Test getting a non-existent module."""
        from minio.error import S3Error

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        error = S3Error(
            code="NoSuchKey",
            message="Not found",
            resource="test",
            request_id="req-1",
            host_id="host-1",
            response=MagicMock(),
        )
        mock_client.get_object.side_effect = error

        result = storage.get_module("pub-1", "book-123", "TestBook", 999)

        assert result is None

    @patch("app.services.topic_analysis.storage.get_minio_client")
    def test_update_module_with_topics(self, mock_get_client, storage):
        """Test updating a module with topic analysis results."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock existing module
        existing = {
            "module_id": 1,
            "title": "Test",
            "text": "Content",
            "topics": [],
            "language": "",
            "difficulty": "",
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(existing).encode()
        mock_client.get_object.return_value = mock_response

        module_result = ModuleAnalysisResult(
            module_id=1,
            module_title="Test",
            topic_result=TopicResult(
                topics=["greetings"],
                grammar_points=["present simple"],
                difficulty="A1",
                language="en",
                target_skills=["reading"],
            ),
            success=True,
        )

        path = storage.update_module_with_topics(
            publisher_id="pub-1",
            book_id="book-123",
            book_name="TestBook",
            module_result=module_result,
        )

        assert path is not None
        mock_client.put_object.assert_called_once()

        # Verify the updated data
        call_args = mock_client.put_object.call_args
        assert call_args[0][0] == "publishers"  # bucket
        assert "module_1.json" in call_args[0][1]  # path

    @patch("app.services.topic_analysis.storage.get_minio_client")
    def test_list_modules(self, mock_get_client, storage):
        """Test listing modules for a book."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock list_objects response
        mock_obj1 = MagicMock()
        mock_obj1.object_name = "pub-1/books/book-123/Test/ai-data/modules/module_1.json"

        mock_obj2 = MagicMock()
        mock_obj2.object_name = "pub-1/books/book-123/Test/ai-data/modules/module_2.json"

        mock_metadata = MagicMock()
        mock_metadata.object_name = "pub-1/books/book-123/Test/ai-data/modules/segmentation_metadata.json"

        mock_client.list_objects.return_value = [mock_obj1, mock_obj2, mock_metadata]

        # Mock get_object for each module
        module1 = {"module_id": 1, "title": "Unit 1"}
        module2 = {"module_id": 2, "title": "Unit 2"}

        mock_response1 = MagicMock()
        mock_response1.read.return_value = json.dumps(module1).encode()

        mock_response2 = MagicMock()
        mock_response2.read.return_value = json.dumps(module2).encode()

        mock_client.get_object.side_effect = [mock_response1, mock_response2]

        result = storage.list_modules("pub-1", "book-123", "Test")

        assert len(result) == 2
        assert result[0]["module_id"] == 1
        assert result[1]["module_id"] == 2


# =============================================================================
# Test Enums
# =============================================================================


class TestEnums:
    """Tests for enum values."""

    def test_cefr_levels(self):
        """Test CEFR level enum values."""
        assert CEFRLevel.A1.value == "A1"
        assert CEFRLevel.A2.value == "A2"
        assert CEFRLevel.B1.value == "B1"
        assert CEFRLevel.B2.value == "B2"
        assert CEFRLevel.C1.value == "C1"
        assert CEFRLevel.C2.value == "C2"

    def test_target_skills(self):
        """Test target skill enum values."""
        assert TargetSkill.READING.value == "reading"
        assert TargetSkill.WRITING.value == "writing"
        assert TargetSkill.SPEAKING.value == "speaking"
        assert TargetSkill.LISTENING.value == "listening"

    def test_detected_languages(self):
        """Test detected language enum values."""
        assert DetectedLanguage.ENGLISH.value == "en"
        assert DetectedLanguage.TURKISH.value == "tr"
        assert DetectedLanguage.BILINGUAL.value == "bilingual"
        assert DetectedLanguage.UNKNOWN.value == "unknown"
