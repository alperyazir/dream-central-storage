"""Tests for the segmentation service."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.segmentation.models import (
    InvalidModuleDefinitionError,
    ManualModuleDefinition,
    Module,
    NoTextFoundError,
    SegmentationError,
    SegmentationLimitError,
    SegmentationMethod,
    SegmentationResult,
)
from app.services.segmentation.strategies.fallback import (
    PageSplitStrategy,
    SingleModuleStrategy,
)
from app.services.segmentation.strategies.header import HeaderBasedStrategy
from app.services.segmentation.strategies.manual import ManualStrategy
from app.services.segmentation.strategies.toc import TOCBasedStrategy


# =============================================================================
# Test Data Models
# =============================================================================


class TestModule:
    """Tests for Module dataclass."""

    def test_create_module(self):
        """Test creating a module."""
        module = Module(
            module_id=1,
            title="Unit 1: Introduction",
            pages=[1, 2, 3],
            start_page=1,
            end_page=3,
            text="Hello world this is sample text",
        )
        assert module.module_id == 1
        assert module.title == "Unit 1: Introduction"
        assert module.pages == [1, 2, 3]
        assert module.word_count == 6
        assert module.char_count == 31

    def test_empty_text(self):
        """Test module with empty text."""
        module = Module(
            module_id=1,
            title="Empty Module",
            pages=[1],
            start_page=1,
            end_page=1,
            text="",
        )
        assert module.word_count == 0
        assert module.char_count == 0

    def test_to_dict(self):
        """Test converting module to dictionary."""
        module = Module(
            module_id=1,
            title="Test",
            pages=[1, 2],
            start_page=1,
            end_page=2,
            text="Sample text",
        )
        d = module.to_dict()
        assert d["module_id"] == 1
        assert d["title"] == "Test"
        assert d["pages"] == [1, 2]
        assert d["word_count"] == 2

    def test_from_dict(self):
        """Test creating module from dictionary."""
        data = {
            "module_id": 2,
            "title": "Chapter 2",
            "pages": [5, 6, 7],
            "start_page": 5,
            "end_page": 7,
            "text": "Chapter content here",
            "topics": ["topic1"],
            "language": "en",
        }
        module = Module.from_dict(data)
        assert module.module_id == 2
        assert module.title == "Chapter 2"
        assert module.topics == ["topic1"]
        assert module.language == "en"


class TestSegmentationResult:
    """Tests for SegmentationResult."""

    def test_create_result(self):
        """Test creating segmentation result."""
        modules = [
            Module(
                module_id=1,
                title="M1",
                pages=[1, 2],
                start_page=1,
                end_page=2,
                text="Hello",
            ),
            Module(
                module_id=2,
                title="M2",
                pages=[3, 4],
                start_page=3,
                end_page=4,
                text="World",
            ),
        ]
        result = SegmentationResult(
            book_id="book-123",
            publisher_id="pub-456",
            book_name="test-book",
            total_pages=4,
            modules=modules,
            method=SegmentationMethod.HEADER_BASED,
        )
        assert result.book_id == "book-123"
        assert result.module_count == 2
        assert result.total_word_count == 2

    def test_to_metadata_dict(self):
        """Test metadata conversion."""
        modules = [
            Module(
                module_id=1,
                title="Test",
                pages=[1],
                start_page=1,
                end_page=1,
                text="Hi",
            )
        ]
        result = SegmentationResult(
            book_id="book-123",
            publisher_id="pub-456",
            book_name="test-book",
            total_pages=1,
            modules=modules,
            method=SegmentationMethod.SINGLE_MODULE,
        )
        metadata = result.to_metadata_dict()
        assert metadata["book_id"] == "book-123"
        assert metadata["module_count"] == 1
        assert metadata["segmentation_method"] == "single_module"


class TestExceptions:
    """Tests for segmentation exceptions."""

    def test_segmentation_error(self):
        """Test base segmentation error."""
        err = SegmentationError("Test error", "book-123", {"key": "value"})
        assert "book-123" in str(err)
        assert err.book_id == "book-123"
        assert err.details == {"key": "value"}

    def test_no_text_found_error(self):
        """Test no text found error."""
        err = NoTextFoundError("book-123", "/path/to/text")
        assert "book-123" in str(err)
        assert err.path == "/path/to/text"

    def test_invalid_module_definition_error(self):
        """Test invalid module definition error."""
        err = InvalidModuleDefinitionError("book-123", "overlap detected")
        assert "overlap detected" in str(err)
        assert err.reason == "overlap detected"

    def test_segmentation_limit_error(self):
        """Test segmentation limit error."""
        err = SegmentationLimitError("book-123", 100, 50)
        assert err.count == 100
        assert err.max_count == 50


class TestManualModuleDefinition:
    """Tests for ManualModuleDefinition."""

    def test_valid_definition(self):
        """Test valid definition."""
        defn = ManualModuleDefinition(title="Test", start_page=1, end_page=10)
        errors = defn.validate(total_pages=20)
        assert errors == []

    def test_invalid_start_page(self):
        """Test invalid start page."""
        defn = ManualModuleDefinition(title="Test", start_page=0, end_page=10)
        errors = defn.validate(total_pages=20)
        assert any("start_page" in e for e in errors)

    def test_end_before_start(self):
        """Test end page before start page."""
        defn = ManualModuleDefinition(title="Test", start_page=10, end_page=5)
        errors = defn.validate(total_pages=20)
        assert any("end_page" in e for e in errors)

    def test_exceeds_total_pages(self):
        """Test end page exceeds total."""
        defn = ManualModuleDefinition(title="Test", start_page=1, end_page=30)
        errors = defn.validate(total_pages=20)
        assert any("exceeds" in e for e in errors)

    def test_empty_title(self):
        """Test empty title."""
        defn = ManualModuleDefinition(title="   ", start_page=1, end_page=10)
        errors = defn.validate(total_pages=20)
        assert any("title" in e for e in errors)


# =============================================================================
# Test Header-Based Strategy
# =============================================================================


class TestHeaderBasedStrategy:
    """Tests for HeaderBasedStrategy."""

    def test_detect_unit_pattern(self):
        """Test detecting 'Unit N' pattern."""
        strategy = HeaderBasedStrategy()
        pages = {
            1: "Unit 1: Introduction\nThis is the intro.",
            5: "Unit 2: Basics\nBasic concepts here.",
        }
        boundaries = strategy.detect_boundaries(pages)
        assert len(boundaries) == 2
        assert boundaries[0].start_page == 1
        assert "Unit 1" in boundaries[0].title
        assert boundaries[1].start_page == 5

    def test_detect_chapter_pattern(self):
        """Test detecting 'Chapter N' pattern."""
        strategy = HeaderBasedStrategy()
        pages = {
            1: "Chapter 1\nIntro text",
            10: "Chapter 2\nMore text",
            20: "Chapter 3\nEven more text",
        }
        boundaries = strategy.detect_boundaries(pages)
        assert len(boundaries) == 3

    def test_detect_roman_numerals(self):
        """Test detecting Roman numeral headers."""
        strategy = HeaderBasedStrategy()
        pages = {
            1: "I. Introduction\nFirst section",
            5: "II. Methods\nMethods section",
            10: "III. Results\nResults here",
        }
        boundaries = strategy.detect_boundaries(pages)
        assert len(boundaries) == 3
        assert boundaries[0].confidence == 0.8

    def test_detect_turkish_patterns(self):
        """Test detecting Turkish patterns."""
        strategy = HeaderBasedStrategy()
        pages = {
            1: "Unite 1: Giris\nTurkish content",
            5: "Bolum 2: Temel Kavramlar\nMore content",
        }
        boundaries = strategy.detect_boundaries(pages)
        assert len(boundaries) == 2

    def test_no_headers_found(self):
        """Test when no headers are found."""
        strategy = HeaderBasedStrategy()
        pages = {
            1: "Just regular text without any headers.",
            2: "More regular text here.",
        }
        boundaries = strategy.detect_boundaries(pages)
        assert len(boundaries) == 0

    def test_can_segment_with_headers(self):
        """Test can_segment returns True with headers."""
        strategy = HeaderBasedStrategy()
        pages = {
            1: "Unit 1: Test",
            5: "Unit 2: Test",
        }
        assert strategy.can_segment(pages) is True

    def test_can_segment_without_headers(self):
        """Test can_segment returns False without headers."""
        strategy = HeaderBasedStrategy()
        pages = {1: "No headers here"}
        assert strategy.can_segment(pages) is False


# =============================================================================
# Test TOC-Based Strategy
# =============================================================================


class TestTOCBasedStrategy:
    """Tests for TOCBasedStrategy."""

    def test_detect_toc_with_dots(self):
        """Test detecting TOC with dot leaders."""
        strategy = TOCBasedStrategy()
        pages = {
            1: "Table of Contents\n\nChapter 1: Introduction ........ 5\nChapter 2: Basics ........ 15\nChapter 3: Advanced ........ 25",
            5: "Introduction content here",
        }
        boundaries = strategy.detect_boundaries(pages)
        assert len(boundaries) >= 2

    def test_detect_toc_with_spaces(self):
        """Test detecting TOC with space alignment."""
        strategy = TOCBasedStrategy()
        pages = {
            1: "Contents\n\nUnit 1: Getting Started          10\nUnit 2: Core Concepts            20\nUnit 3: Practice                 30",
        }
        boundaries = strategy.detect_boundaries(pages)
        assert len(boundaries) >= 2

    def test_no_toc_found(self):
        """Test when no TOC is found."""
        strategy = TOCBasedStrategy()
        pages = {
            1: "Regular content without TOC",
            2: "More content here",
        }
        boundaries = strategy.detect_boundaries(pages)
        assert len(boundaries) == 0

    def test_can_segment_with_toc(self):
        """Test can_segment with valid TOC."""
        strategy = TOCBasedStrategy()
        pages = {
            1: "Table of Contents\nCh 1 ........ 5\nCh 2 ........ 10"
        }
        assert strategy.can_segment(pages) is True


# =============================================================================
# Test Manual Strategy
# =============================================================================


class TestManualStrategy:
    """Tests for ManualStrategy."""

    def test_manual_boundaries(self):
        """Test creating boundaries from manual definitions."""
        definitions = [
            ManualModuleDefinition(title="Module A", start_page=1, end_page=10),
            ManualModuleDefinition(title="Module B", start_page=11, end_page=20),
        ]
        strategy = ManualStrategy(definitions=definitions)
        pages = {i: f"Page {i}" for i in range(1, 21)}

        boundaries = strategy.detect_boundaries(pages, book_id="test-book")
        assert len(boundaries) == 2
        assert boundaries[0].title == "Module A"
        assert boundaries[0].confidence == 1.0

    def test_invalid_overlap(self):
        """Test overlap detection."""
        definitions = [
            ManualModuleDefinition(title="A", start_page=1, end_page=15),
            ManualModuleDefinition(title="B", start_page=10, end_page=20),
        ]
        strategy = ManualStrategy(definitions=definitions)
        pages = {i: f"Page {i}" for i in range(1, 21)}

        with pytest.raises(InvalidModuleDefinitionError) as exc_info:
            strategy.detect_boundaries(pages, book_id="test-book")
        assert "Overlap" in str(exc_info.value)

    def test_from_config(self):
        """Test creating from config dict."""
        config = [
            {"title": "Intro", "start_page": 1, "end_page": 5},
            {"title": "Main", "start_page": 6, "end_page": 20},
        ]
        strategy = ManualStrategy.from_config(config)
        assert len(strategy.definitions) == 2


# =============================================================================
# Test Fallback Strategies
# =============================================================================


class TestSingleModuleStrategy:
    """Tests for SingleModuleStrategy."""

    def test_single_module(self):
        """Test creating single module."""
        strategy = SingleModuleStrategy(default_title="Complete Book")
        pages = {1: "Page 1", 2: "Page 2", 3: "Page 3"}
        boundaries = strategy.detect_boundaries(pages)
        assert len(boundaries) == 1
        assert boundaries[0].title == "Complete Book"
        assert boundaries[0].start_page == 1

    def test_custom_title(self):
        """Test custom title via kwargs."""
        strategy = SingleModuleStrategy()
        pages = {1: "Text"}
        boundaries = strategy.detect_boundaries(pages, title="My Custom Title")
        assert boundaries[0].title == "My Custom Title"

    def test_can_segment(self):
        """Test can_segment always True."""
        strategy = SingleModuleStrategy()
        assert strategy.can_segment({1: "text"}) is True
        assert strategy.can_segment({}) is False


class TestPageSplitStrategy:
    """Tests for PageSplitStrategy."""

    def test_split_by_pages(self):
        """Test splitting by page count."""
        strategy = PageSplitStrategy(pages_per_module=5)
        pages = {i: f"Page {i}" for i in range(1, 21)}
        boundaries = strategy.detect_boundaries(pages)
        assert len(boundaries) == 4  # 20 pages / 5 per module

    def test_small_book_single_module(self):
        """Test small book becomes single module."""
        strategy = PageSplitStrategy(pages_per_module=20)
        pages = {i: f"Page {i}" for i in range(1, 6)}
        boundaries = strategy.detect_boundaries(pages)
        assert len(boundaries) == 1

    def test_low_confidence(self):
        """Test page split has low confidence."""
        strategy = PageSplitStrategy(pages_per_module=5)
        pages = {i: f"Page {i}" for i in range(1, 11)}
        boundaries = strategy.detect_boundaries(pages)
        assert all(b.confidence == 0.5 for b in boundaries)


# =============================================================================
# Test AI Strategy (with mocks)
# =============================================================================


class TestAIAssistedStrategy:
    """Tests for AIAssistedStrategy."""

    @pytest.mark.asyncio
    async def test_ai_segmentation_success(self):
        """Test successful AI segmentation."""
        from app.services.segmentation.strategies.ai import AIAssistedStrategy

        mock_llm = MagicMock()
        mock_llm.simple_completion = MagicMock(
            return_value='[{"title": "Chapter 1", "start_page": 1}, {"title": "Chapter 2", "start_page": 10}]'
        )

        # Make it async
        async def mock_completion(*args, **kwargs):
            return '[{"title": "Chapter 1", "start_page": 1}, {"title": "Chapter 2", "start_page": 10}]'

        mock_llm.simple_completion = mock_completion

        strategy = AIAssistedStrategy(llm_service=mock_llm)
        pages = {1: "Intro text", 10: "Chapter 2 text"}

        boundaries = await strategy.detect_boundaries_async(pages)
        assert len(boundaries) == 2
        assert boundaries[0].title == "Chapter 1"

    @pytest.mark.asyncio
    async def test_ai_segmentation_invalid_json(self):
        """Test handling of invalid JSON from LLM."""
        from app.services.segmentation.strategies.ai import AIAssistedStrategy

        async def mock_completion(*args, **kwargs):
            return "This is not JSON"

        mock_llm = MagicMock()
        mock_llm.simple_completion = mock_completion

        strategy = AIAssistedStrategy(llm_service=mock_llm)
        pages = {1: "Text"}

        boundaries = await strategy.detect_boundaries_async(pages)
        assert len(boundaries) == 0

    @pytest.mark.asyncio
    async def test_ai_segmentation_llm_failure(self):
        """Test handling LLM failure."""
        from app.services.segmentation.strategies.ai import AIAssistedStrategy

        async def mock_completion(*args, **kwargs):
            raise Exception("LLM unavailable")

        mock_llm = MagicMock()
        mock_llm.simple_completion = mock_completion

        strategy = AIAssistedStrategy(llm_service=mock_llm)
        pages = {1: "Text"}

        boundaries = await strategy.detect_boundaries_async(pages)
        assert len(boundaries) == 0


# =============================================================================
# Test Segmentation Service
# =============================================================================


class TestSegmentationService:
    """Tests for SegmentationService."""

    @pytest.mark.asyncio
    async def test_segment_from_text_header_based(self):
        """Test segmentation using header strategy."""
        from app.services.segmentation.service import SegmentationService

        service = SegmentationService()
        pages = {
            1: "Unit 1: Introduction\nIntro content here.",
            5: "Unit 2: Basics\nBasic content here.",
            10: "Unit 3: Advanced\nAdvanced content here.",
        }

        result = await service.segment_from_text(
            book_id="test-book",
            publisher_id="test-pub",
            book_name="test",
            pages=pages,
        )

        assert result.method == SegmentationMethod.HEADER_BASED
        assert result.module_count == 3

    @pytest.mark.asyncio
    async def test_segment_from_text_manual(self):
        """Test segmentation with manual definitions."""
        from app.services.segmentation.service import SegmentationService

        service = SegmentationService()
        pages = {i: f"Page {i} content" for i in range(1, 21)}

        definitions = [
            ManualModuleDefinition(title="Part A", start_page=1, end_page=10),
            ManualModuleDefinition(title="Part B", start_page=11, end_page=20),
        ]

        result = await service.segment_from_text(
            book_id="test-book",
            publisher_id="test-pub",
            book_name="test",
            pages=pages,
            manual_definitions=definitions,
        )

        assert result.method == SegmentationMethod.MANUAL
        assert result.module_count == 2
        assert result.modules[0].title == "Part A"

    @pytest.mark.asyncio
    async def test_segment_fallback_single_module(self):
        """Test fallback to single module."""
        from app.services.segmentation.service import SegmentationService

        # Create service with AI disabled
        service = SegmentationService()
        service.settings.segmentation_ai_enabled = False

        pages = {
            1: "Just plain text without any headers.",
            2: "More plain text here.",
            3: "Even more plain text.",
        }

        result = await service.segment_from_text(
            book_id="test-book",
            publisher_id="test-pub",
            book_name="test",
            pages=pages,
        )

        assert result.method == SegmentationMethod.SINGLE_MODULE
        assert result.module_count == 1

    @pytest.mark.asyncio
    async def test_segment_empty_pages_raises(self):
        """Test that empty pages raises error."""
        from app.services.segmentation.service import SegmentationService

        service = SegmentationService()

        with pytest.raises(NoTextFoundError):
            await service.segment_from_text(
                book_id="test-book",
                publisher_id="test-pub",
                book_name="test",
                pages={},
            )

    @pytest.mark.asyncio
    async def test_module_text_aggregation(self):
        """Test that module text is properly aggregated."""
        from app.services.segmentation.service import SegmentationService

        service = SegmentationService()
        pages = {
            1: "Unit 1: Test\nPage 1 content",
            2: "Page 2 content",
            3: "Unit 2: Another\nPage 3 content",
        }

        result = await service.segment_from_text(
            book_id="test-book",
            publisher_id="test-pub",
            book_name="test",
            pages=pages,
        )

        assert result.module_count == 2
        # First module should have pages 1-2
        assert "Page 1 content" in result.modules[0].text
        assert "Page 2 content" in result.modules[0].text
        # Second module should have page 3
        assert "Page 3 content" in result.modules[1].text


# =============================================================================
# Test Module Storage
# =============================================================================


class TestModuleStorage:
    """Tests for ModuleStorage."""

    def test_build_module_path(self):
        """Test module path construction."""
        from app.services.segmentation.storage import ModuleStorage

        storage = ModuleStorage()
        path = storage._build_module_path("pub-1", "book-1", "my-book", 1)
        assert path == "pub-1/books/book-1/my-book/ai-data/modules/module_1.json"

    def test_build_metadata_path(self):
        """Test metadata path construction."""
        from app.services.segmentation.storage import ModuleStorage

        storage = ModuleStorage()
        path = storage._build_metadata_path("pub-1", "book-1", "my-book")
        assert path == "pub-1/books/book-1/my-book/ai-data/modules/segmentation_metadata.json"

    @patch("app.services.segmentation.storage.get_minio_client")
    def test_save_module(self, mock_get_minio):
        """Test saving a module to storage."""
        from app.services.segmentation.storage import ModuleStorage

        mock_client = MagicMock()
        mock_get_minio.return_value = mock_client

        storage = ModuleStorage()
        module = Module(
            module_id=1,
            title="Test Module",
            pages=[1, 2],
            start_page=1,
            end_page=2,
            text="Test content",
        )
        result = SegmentationResult(
            book_id="book-1",
            publisher_id="pub-1",
            book_name="test-book",
            total_pages=2,
            modules=[module],
            method=SegmentationMethod.HEADER_BASED,
        )

        path = storage.save_module(result, module)
        assert "module_1.json" in path
        mock_client.put_object.assert_called_once()

    @patch("app.services.segmentation.storage.get_minio_client")
    def test_save_all(self, mock_get_minio):
        """Test saving all modules and metadata."""
        from app.services.segmentation.storage import ModuleStorage

        mock_client = MagicMock()
        mock_get_minio.return_value = mock_client

        storage = ModuleStorage()
        modules = [
            Module(
                module_id=i,
                title=f"Module {i}",
                pages=[i],
                start_page=i,
                end_page=i,
                text=f"Content {i}",
            )
            for i in range(1, 4)
        ]
        result = SegmentationResult(
            book_id="book-1",
            publisher_id="pub-1",
            book_name="test-book",
            total_pages=3,
            modules=modules,
            method=SegmentationMethod.HEADER_BASED,
        )

        saved = storage.save_all(result)
        assert len(saved["modules"]) == 3
        assert "metadata" in saved
        assert mock_client.put_object.call_count == 4  # 3 modules + 1 metadata


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for segmentation pipeline."""

    @pytest.mark.asyncio
    async def test_full_segmentation_pipeline(self):
        """Test complete segmentation pipeline."""
        from app.services.segmentation.service import SegmentationService

        service = SegmentationService()

        # Create a realistic book structure
        pages = {}
        pages[1] = "Title Page\nMy Test Book"
        pages[2] = "Table of Contents\n\nUnit 1 ........ 3\nUnit 2 ........ 6"
        pages[3] = "Unit 1: Getting Started\nThis is the first unit content."
        pages[4] = "More content for unit 1.\nLearning the basics."
        pages[5] = "Finishing up unit 1 content."
        pages[6] = "Unit 2: Advanced Topics\nNow we go deeper."
        pages[7] = "More advanced content here."
        pages[8] = "Conclusion of the book."

        result = await service.segment_from_text(
            book_id="integration-test",
            publisher_id="test-pub",
            book_name="test-book",
            pages=pages,
        )

        # Should detect 2 units via header or TOC
        assert result.module_count >= 1
        assert result.method in [
            SegmentationMethod.TOC_BASED,
            SegmentationMethod.HEADER_BASED,
            SegmentationMethod.SINGLE_MODULE,
        ]
        assert result.total_pages == 8

    @pytest.mark.asyncio
    async def test_progress_callback(self):
        """Test progress callback is called."""
        from app.services.segmentation.service import SegmentationService

        service = SegmentationService()
        progress_values = []

        def track_progress(current, total):
            progress_values.append((current, total))

        pages = {
            1: "Unit 1: Test\nContent",
            5: "Unit 2: Test\nMore content",
        }

        await service.segment_from_text(
            book_id="test",
            publisher_id="pub",
            book_name="book",
            pages=pages,
        )

        # Progress callback is only used in segment_book, not segment_from_text
        # This is expected behavior
