"""Tests for PDF extraction service."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.pdf.detector import ScannedPDFDetector
from app.services.pdf.extractor import PDFExtractor
from app.services.pdf.models import (
    ExtractionMethod,
    OCRError,
    PageText,
    PDFAnalysisResult,
    PDFCorruptedError,
    PDFExtractionError,
    PDFExtractionResult,
    PDFNotFoundError,
    PDFPageLimitExceededError,
    PDFPasswordProtectedError,
)
from app.services.pdf.ocr import PDFOCRService
from app.services.pdf.service import PDFExtractionService
from app.services.pdf.storage import AIDataStorage


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Create a simple test PDF with text content using PyMuPDF."""
    import fitz

    doc = fitz.open()
    # Page 1 with text
    page1 = doc.new_page()
    page1.insert_text((50, 50), "This is page one with sample text content.")
    page1.insert_text((50, 80), "It has multiple lines of text for testing.")

    # Page 2 with text
    page2 = doc.new_page()
    page2.insert_text((50, 50), "This is page two.")
    page2.insert_text((50, 80), "More text on the second page.")

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def minimal_text_pdf_bytes() -> bytes:
    """Create a PDF with minimal text (simulates scanned page)."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hi")  # Very short text
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def empty_pdf_bytes() -> bytes:
    """Create a PDF with no text (blank page)."""
    import fitz

    doc = fitz.open()
    doc.new_page()  # Empty page
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.pdf_min_text_threshold = 50
    settings.pdf_min_word_threshold = 10
    settings.pdf_ocr_enabled = True
    settings.pdf_ocr_batch_size = 5
    settings.pdf_ocr_dpi = 150
    settings.pdf_max_pages = 500
    settings.minio_publishers_bucket = "publishers"
    settings.minio_endpoint = "localhost:9000"
    settings.minio_access_key = "test"
    settings.minio_secret_key = "test"
    settings.minio_secure = False
    return settings


@pytest.fixture
def mock_llm_response():
    """Create mock LLM response for OCR tests."""
    from app.services.llm.base import LLMResponse, LLMUsage

    return LLMResponse(
        content="OCR extracted text from image",
        usage=LLMUsage(prompt_tokens=100, completion_tokens=50),
        model="gemini-1.5-flash",
        provider="gemini",
    )


# =============================================================================
# Model Tests
# =============================================================================


class TestPageText:
    """Tests for PageText dataclass."""

    def test_create_page_text(self):
        page = PageText(page_number=1, text="Hello world", method=ExtractionMethod.NATIVE)
        assert page.page_number == 1
        assert page.text == "Hello world"
        assert page.method == ExtractionMethod.NATIVE
        assert page.word_count == 2
        assert page.char_count == 11

    def test_empty_text(self):
        page = PageText(page_number=1, text="", method=ExtractionMethod.NATIVE)
        assert page.word_count == 0
        assert page.char_count == 0

    def test_whitespace_only_text(self):
        page = PageText(page_number=1, text="   \n\t  ", method=ExtractionMethod.NATIVE)
        assert page.word_count == 0
        assert page.char_count == 7


class TestPDFExtractionResult:
    """Tests for PDFExtractionResult dataclass."""

    def test_create_result(self):
        pages = [
            PageText(page_number=1, text="Hello world", method=ExtractionMethod.NATIVE),
            PageText(page_number=2, text="Second page content", method=ExtractionMethod.NATIVE),
        ]
        result = PDFExtractionResult(
            book_id="book-123",
            publisher_id="pub-456",
            book_name="test-book",
            total_pages=2,
            pages=pages,
            method=ExtractionMethod.NATIVE,
            scanned_page_count=0,
            native_page_count=2,
        )
        assert result.book_id == "book-123"
        assert result.total_pages == 2
        assert result.total_word_count == 5  # 2 + 3
        assert result.total_char_count == 30  # 11 + 19

    def test_to_metadata_dict(self):
        pages = [PageText(page_number=1, text="Test", method=ExtractionMethod.NATIVE)]
        result = PDFExtractionResult(
            book_id="book-123",
            publisher_id="pub-456",
            book_name="test-book",
            total_pages=1,
            pages=pages,
            method=ExtractionMethod.NATIVE,
            scanned_page_count=0,
            native_page_count=1,
        )
        metadata = result.to_metadata_dict()
        assert metadata["book_id"] == "book-123"
        assert metadata["extraction_method"] == "native"
        assert metadata["total_pages"] == 1


class TestExceptions:
    """Tests for PDF extraction exceptions."""

    def test_pdf_extraction_error(self):
        error = PDFExtractionError("Test error", "book-123", {"key": "value"})
        assert "book-123" in str(error)
        assert error.book_id == "book-123"
        assert error.details == {"key": "value"}

    def test_pdf_not_found_error(self):
        error = PDFNotFoundError("book-123", "/path/to/pdf")
        assert "not found" in str(error).lower()
        assert error.path == "/path/to/pdf"

    def test_pdf_password_protected_error(self):
        error = PDFPasswordProtectedError("book-123")
        assert "password" in str(error).lower()

    def test_pdf_corrupted_error(self):
        error = PDFCorruptedError("book-123", "Invalid header")
        assert "corrupted" in str(error).lower()
        assert error.reason == "Invalid header"

    def test_ocr_error(self):
        error = OCRError("book-123", 5, "API timeout")
        assert "page 5" in str(error).lower()
        assert error.page == 5
        assert error.reason == "API timeout"

    def test_page_limit_exceeded_error(self):
        error = PDFPageLimitExceededError("book-123", 600, 500)
        assert error.page_count == 600
        assert error.max_pages == 500


# =============================================================================
# PDF Extractor Tests
# =============================================================================


class TestPDFExtractor:
    """Tests for PDFExtractor class."""

    def test_open_valid_pdf(self, sample_pdf_bytes):
        extractor = PDFExtractor(sample_pdf_bytes, "book-123")
        extractor.open()
        assert extractor.page_count == 2
        extractor.close()

    def test_context_manager(self, sample_pdf_bytes):
        with PDFExtractor(sample_pdf_bytes, "book-123") as extractor:
            assert extractor.page_count == 2

    def test_extract_text_from_page(self, sample_pdf_bytes):
        with PDFExtractor(sample_pdf_bytes, "book-123") as extractor:
            text = extractor.extract_text_from_page(0)
            assert "page one" in text.lower()
            assert "sample text" in text.lower()

    def test_extract_all_pages(self, sample_pdf_bytes):
        with PDFExtractor(sample_pdf_bytes, "book-123") as extractor:
            pages = extractor.extract_all_pages()
            assert len(pages) == 2
            assert pages[0].page_number == 1
            assert pages[1].page_number == 2
            assert pages[0].method == ExtractionMethod.NATIVE

    def test_extract_with_progress_callback(self, sample_pdf_bytes):
        progress_calls = []

        def callback(current, total):
            progress_calls.append((current, total))

        with PDFExtractor(sample_pdf_bytes, "book-123") as extractor:
            extractor.extract_all_pages(progress_callback=callback)

        assert len(progress_calls) == 2
        assert progress_calls[0] == (1, 2)
        assert progress_calls[1] == (2, 2)

    def test_page_to_image(self, sample_pdf_bytes):
        with PDFExtractor(sample_pdf_bytes, "book-123") as extractor:
            image_bytes = extractor.page_to_image(0, dpi=72)
            # Check PNG magic bytes
            assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    def test_open_corrupted_pdf(self):
        corrupted_data = b"not a valid pdf"
        extractor = PDFExtractor(corrupted_data, "book-123")
        with pytest.raises(PDFCorruptedError):
            extractor.open()

    def test_page_out_of_range(self, sample_pdf_bytes):
        with PDFExtractor(sample_pdf_bytes, "book-123") as extractor:
            with pytest.raises(IndexError):
                extractor.extract_text_from_page(10)

    def test_extract_without_open_raises_error(self, sample_pdf_bytes):
        extractor = PDFExtractor(sample_pdf_bytes, "book-123")
        with pytest.raises(RuntimeError, match="not opened"):
            extractor.extract_text_from_page(0)


# =============================================================================
# Scanned PDF Detector Tests
# =============================================================================


class TestScannedPDFDetector:
    """Tests for ScannedPDFDetector class."""

    def test_detect_native_page(self):
        detector = ScannedPDFDetector(min_char_threshold=50, min_word_threshold=10)
        # Text with plenty of content
        text = "This is a page with plenty of text content. " * 5
        assert detector.is_scanned_page(text) is False

    def test_detect_scanned_page_by_chars(self):
        detector = ScannedPDFDetector(min_char_threshold=50, min_word_threshold=10)
        # Short text (less than 50 chars)
        text = "Short text"
        assert detector.is_scanned_page(text) is True

    def test_detect_scanned_page_by_words(self):
        detector = ScannedPDFDetector(min_char_threshold=50, min_word_threshold=10)
        # Few words but long chars (like a single long word repeated)
        text = "a" * 100  # 100 chars but 1 word
        assert detector.is_scanned_page(text) is True

    def test_detect_empty_page(self):
        detector = ScannedPDFDetector()
        assert detector.is_scanned_page("") is True
        assert detector.is_scanned_page("   ") is True

    def test_analyze_page_texts_all_native(self):
        detector = ScannedPDFDetector(min_char_threshold=50, min_word_threshold=10)
        texts = [
            "This is page one with plenty of text content for testing.",
            "This is page two with even more text content for analysis.",
        ]
        result = detector.analyze_page_texts(texts)
        assert result.total_pages == 2
        assert result.native_pages == 2
        assert result.scanned_pages == 0
        assert result.classification == ExtractionMethod.NATIVE

    def test_analyze_page_texts_all_scanned(self):
        detector = ScannedPDFDetector(min_char_threshold=50, min_word_threshold=10)
        texts = ["Hi", ""]  # Very short texts
        result = detector.analyze_page_texts(texts)
        assert result.scanned_pages == 2
        assert result.native_pages == 0
        assert result.classification == ExtractionMethod.OCR

    def test_analyze_page_texts_mixed(self):
        detector = ScannedPDFDetector(min_char_threshold=50, min_word_threshold=10)
        texts = [
            "This is a page with plenty of text content for testing purposes.",
            "Hi",  # Scanned
        ]
        result = detector.analyze_page_texts(texts)
        assert result.scanned_pages == 1
        assert result.native_pages == 1
        assert result.classification == ExtractionMethod.MIXED
        assert result.scanned_page_numbers == [2]


# =============================================================================
# OCR Service Tests
# =============================================================================


class TestPDFOCRService:
    """Tests for PDFOCRService class."""

    @pytest.mark.asyncio
    async def test_ocr_page_success(self, mock_llm_response):
        with patch("app.services.pdf.ocr.get_llm_service") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.complete_with_vision = AsyncMock(return_value=mock_llm_response)
            mock_get_llm.return_value = mock_llm

            ocr_service = PDFOCRService(book_id="book-123")
            result = await ocr_service.ocr_page(b"fake_image_bytes", page_number=1)

            assert result == "OCR extracted text from image"
            mock_llm.complete_with_vision.assert_called_once()

    @pytest.mark.asyncio
    async def test_ocr_page_retry_on_failure(self, mock_llm_response):
        from app.services.llm.base import LLMProviderError

        with patch("app.services.pdf.ocr.get_llm_service") as mock_get_llm:
            mock_llm = MagicMock()
            # First call fails, second succeeds
            mock_llm.complete_with_vision = AsyncMock(
                side_effect=[
                    LLMProviderError("Temporary error", provider="gemini"),
                    mock_llm_response,
                ]
            )
            mock_get_llm.return_value = mock_llm

            ocr_service = PDFOCRService(book_id="book-123", max_retries=2, retry_delay=0.01)
            result = await ocr_service.ocr_page(b"fake_image_bytes", page_number=1)

            assert result == "OCR extracted text from image"
            assert mock_llm.complete_with_vision.call_count == 2

    @pytest.mark.asyncio
    async def test_ocr_page_all_retries_fail(self):
        from app.services.llm.base import LLMProviderError

        with patch("app.services.pdf.ocr.get_llm_service") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.complete_with_vision = AsyncMock(
                side_effect=LLMProviderError("Persistent error", provider="gemini")
            )
            mock_get_llm.return_value = mock_llm

            ocr_service = PDFOCRService(book_id="book-123", max_retries=2, retry_delay=0.01)

            with pytest.raises(OCRError) as exc_info:
                await ocr_service.ocr_page(b"fake_image_bytes", page_number=5)

            assert exc_info.value.page == 5


# =============================================================================
# PDF Extraction Service Tests
# =============================================================================


class TestPDFExtractionService:
    """Tests for unified PDFExtractionService."""

    @pytest.mark.asyncio
    async def test_extract_from_bytes_native(self, sample_pdf_bytes, mock_settings):
        mock_settings.pdf_ocr_enabled = False  # Disable OCR for this test

        service = PDFExtractionService(settings=mock_settings)
        result = await service.extract_from_bytes(
            pdf_data=sample_pdf_bytes,
            book_id="book-123",
            publisher_id="pub-456",
            book_name="test-book",
        )

        assert result.book_id == "book-123"
        assert result.total_pages == 2
        assert result.method == ExtractionMethod.NATIVE
        assert len(result.pages) == 2

    @pytest.mark.asyncio
    async def test_extract_with_progress_callback(self, sample_pdf_bytes, mock_settings):
        mock_settings.pdf_ocr_enabled = False

        progress_calls = []

        def callback(current, total):
            progress_calls.append((current, total))

        service = PDFExtractionService(settings=mock_settings)
        await service.extract_from_bytes(
            pdf_data=sample_pdf_bytes,
            book_id="book-123",
            publisher_id="pub-456",
            book_name="test-book",
            progress_callback=callback,
        )

        # Final progress should be reported
        assert progress_calls[-1] == (2, 2)

    @pytest.mark.asyncio
    async def test_page_limit_exceeded(self, sample_pdf_bytes, mock_settings):
        mock_settings.pdf_max_pages = 1  # Set limit lower than PDF page count

        service = PDFExtractionService(settings=mock_settings)

        with pytest.raises(PDFPageLimitExceededError) as exc_info:
            await service.extract_from_bytes(
                pdf_data=sample_pdf_bytes,
                book_id="book-123",
                publisher_id="pub-456",
                book_name="test-book",
            )

        assert exc_info.value.page_count == 2
        assert exc_info.value.max_pages == 1

    @pytest.mark.asyncio
    async def test_extract_book_pdf_not_found(self, mock_settings):
        with patch("app.services.pdf.service.get_minio_client") as mock_minio:
            from minio.error import S3Error

            mock_client = MagicMock()
            mock_client.get_object.side_effect = S3Error(
                code="NoSuchKey",
                message="Not found",
                resource="/path",
                request_id="123",
                host_id="host",
                response=MagicMock(),
            )
            mock_minio.return_value = mock_client

            service = PDFExtractionService(settings=mock_settings)

            with pytest.raises(PDFNotFoundError):
                await service.extract_book_pdf(
                    book_id="book-123",
                    publisher_id="pub-456",
                    book_name="test-book",
                )


# =============================================================================
# AI Data Storage Tests
# =============================================================================


class TestAIDataStorage:
    """Tests for AIDataStorage class."""

    def test_build_text_path(self, mock_settings):
        storage = AIDataStorage(settings=mock_settings)
        path = storage._build_text_path("pub-123", "book-456", "my-book", 1)
        assert path == "pub-123/books/book-456/my-book/ai-data/text/page_001.txt"

    def test_build_text_path_formatting(self, mock_settings):
        storage = AIDataStorage(settings=mock_settings)
        # Test page number formatting
        path = storage._build_text_path("pub-123", "book-456", "my-book", 42)
        assert "page_042.txt" in path

    def test_build_metadata_path(self, mock_settings):
        storage = AIDataStorage(settings=mock_settings)
        path = storage._build_metadata_path("pub-123", "book-456", "my-book")
        assert path == "pub-123/books/book-456/my-book/ai-data/text/extraction_metadata.json"

    def test_save_extracted_text(self, mock_settings):
        with patch("app.services.pdf.storage.get_minio_client") as mock_minio:
            mock_client = MagicMock()
            mock_minio.return_value = mock_client

            storage = AIDataStorage(settings=mock_settings)

            pages = [
                PageText(page_number=1, text="Page one text", method=ExtractionMethod.NATIVE),
                PageText(page_number=2, text="Page two text", method=ExtractionMethod.NATIVE),
            ]
            result = PDFExtractionResult(
                book_id="book-123",
                publisher_id="pub-456",
                book_name="my-book",
                total_pages=2,
                pages=pages,
                method=ExtractionMethod.NATIVE,
                scanned_page_count=0,
                native_page_count=2,
            )

            saved_paths = storage.save_extracted_text(result)

            assert len(saved_paths) == 2
            assert mock_client.put_object.call_count == 2

    def test_save_extraction_metadata(self, mock_settings):
        with patch("app.services.pdf.storage.get_minio_client") as mock_minio:
            mock_client = MagicMock()
            mock_minio.return_value = mock_client

            storage = AIDataStorage(settings=mock_settings)

            pages = [PageText(page_number=1, text="Text", method=ExtractionMethod.NATIVE)]
            result = PDFExtractionResult(
                book_id="book-123",
                publisher_id="pub-456",
                book_name="my-book",
                total_pages=1,
                pages=pages,
                method=ExtractionMethod.NATIVE,
                scanned_page_count=0,
                native_page_count=1,
            )

            path = storage.save_extraction_metadata(result)

            assert "extraction_metadata.json" in path
            mock_client.put_object.assert_called_once()

            # Verify JSON content
            call_args = mock_client.put_object.call_args
            data_arg = call_args[0][2]  # Third positional arg is the data
            json_content = json.loads(data_arg.read().decode("utf-8"))
            assert json_content["book_id"] == "book-123"
            assert json_content["extraction_method"] == "native"

    def test_cleanup_text_directory(self, mock_settings):
        with patch("app.services.pdf.storage.get_minio_client") as mock_minio:
            mock_client = MagicMock()
            # Simulate 3 objects to delete
            mock_obj1 = MagicMock()
            mock_obj1.object_name = "pub/books/book/my-book/ai-data/text/page_001.txt"
            mock_obj2 = MagicMock()
            mock_obj2.object_name = "pub/books/book/my-book/ai-data/text/page_002.txt"
            mock_obj3 = MagicMock()
            mock_obj3.object_name = "pub/books/book/my-book/ai-data/text/metadata.json"
            mock_client.list_objects.return_value = [mock_obj1, mock_obj2, mock_obj3]
            mock_minio.return_value = mock_client

            storage = AIDataStorage(settings=mock_settings)
            deleted = storage.cleanup_text_directory("pub", "book", "my-book")

            assert deleted == 3
            assert mock_client.remove_object.call_count == 3

    def test_text_exists_true(self, mock_settings):
        with patch("app.services.pdf.storage.get_minio_client") as mock_minio:
            mock_client = MagicMock()
            mock_client.stat_object.return_value = MagicMock()  # Object exists
            mock_minio.return_value = mock_client

            storage = AIDataStorage(settings=mock_settings)
            exists = storage.text_exists("pub", "book", "my-book")

            assert exists is True

    def test_text_exists_false(self, mock_settings):
        from minio.error import S3Error

        with patch("app.services.pdf.storage.get_minio_client") as mock_minio:
            mock_client = MagicMock()
            mock_client.stat_object.side_effect = S3Error(
                code="NoSuchKey",
                message="Not found",
                resource="/path",
                request_id="123",
                host_id="host",
                response=MagicMock(),
            )
            mock_minio.return_value = mock_client

            storage = AIDataStorage(settings=mock_settings)
            exists = storage.text_exists("pub", "book", "my-book")

            assert exists is False


# =============================================================================
# Integration Tests (require pymupdf)
# =============================================================================


class TestIntegration:
    """Integration tests that use actual PDF creation."""

    def test_full_extraction_pipeline(self, mock_settings):
        """Test end-to-end extraction without OCR."""
        import fitz

        # Create PDF with sufficient text to pass detection thresholds
        doc = fitz.open()
        page1 = doc.new_page()
        page1.insert_text((50, 50), "This is page one with plenty of text content for testing the extraction pipeline.")
        page1.insert_text((50, 80), "We need enough words and characters to pass the detection thresholds properly.")

        page2 = doc.new_page()
        page2.insert_text((50, 50), "This is page two with additional text content for the second page of our test PDF.")
        page2.insert_text((50, 80), "The detection requires at least fifty characters and ten words per page minimum.")

        pdf_bytes = doc.tobytes()
        doc.close()

        mock_settings.pdf_ocr_enabled = False

        with PDFExtractor(pdf_bytes, "book-123") as extractor:
            pages = extractor.extract_all_pages()

            detector = ScannedPDFDetector(
                min_char_threshold=mock_settings.pdf_min_text_threshold,
                min_word_threshold=mock_settings.pdf_min_word_threshold,
            )
            analysis = detector.analyze_page_texts([p.text for p in pages])

            assert analysis.classification == ExtractionMethod.NATIVE
            assert analysis.total_pages == 2

    def test_multicolumn_text_extraction(self):
        """Test that multi-column layouts are handled."""
        import fitz

        # Create a PDF with text in two columns
        doc = fitz.open()
        page = doc.new_page()

        # Left column
        page.insert_text((50, 50), "Left column line 1")
        page.insert_text((50, 70), "Left column line 2")

        # Right column
        page.insert_text((300, 50), "Right column line 1")
        page.insert_text((300, 70), "Right column line 2")

        pdf_bytes = doc.tobytes()
        doc.close()

        with PDFExtractor(pdf_bytes, "book-123") as extractor:
            text = extractor.extract_text_from_page(0)
            # Both columns should be in the text
            assert "Left column" in text
            assert "Right column" in text
