"""PDF extraction data models and exceptions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ExtractionMethod(str, Enum):
    """Method used for text extraction."""

    NATIVE = "native"  # Text extracted directly from PDF
    OCR = "ocr"  # Text extracted via Gemini Vision OCR
    MIXED = "mixed"  # Some pages native, some OCR


# =============================================================================
# Exceptions
# =============================================================================


class PDFExtractionError(Exception):
    """Base exception for PDF extraction errors."""

    def __init__(
        self, message: str, book_id: str, details: dict[str, Any] | None = None
    ) -> None:
        self.message = message
        self.book_id = book_id
        self.details = details or {}
        super().__init__(f"[{book_id}] {message}")


class PDFNotFoundError(PDFExtractionError):
    """Raised when PDF file is not found in storage."""

    def __init__(self, book_id: str, path: str) -> None:
        super().__init__(f"PDF not found: {path}", book_id, {"path": path})
        self.path = path


class PDFPasswordProtectedError(PDFExtractionError):
    """Raised when PDF is password protected."""

    def __init__(self, book_id: str) -> None:
        super().__init__("PDF is password protected", book_id)


class PDFCorruptedError(PDFExtractionError):
    """Raised when PDF file is corrupted or invalid."""

    def __init__(self, book_id: str, reason: str) -> None:
        super().__init__(f"PDF is corrupted: {reason}", book_id, {"reason": reason})
        self.reason = reason


class OCRError(PDFExtractionError):
    """Raised when OCR processing fails."""

    def __init__(self, book_id: str, page: int, reason: str) -> None:
        super().__init__(
            f"OCR failed for page {page}: {reason}",
            book_id,
            {"page": page, "reason": reason},
        )
        self.page = page
        self.reason = reason


class PDFPageLimitExceededError(PDFExtractionError):
    """Raised when PDF exceeds maximum page limit."""

    def __init__(self, book_id: str, page_count: int, max_pages: int) -> None:
        super().__init__(
            f"PDF has {page_count} pages, exceeds limit of {max_pages}",
            book_id,
            {"page_count": page_count, "max_pages": max_pages},
        )
        self.page_count = page_count
        self.max_pages = max_pages


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class PageText:
    """Extracted text from a single PDF page."""

    page_number: int
    text: str
    method: ExtractionMethod
    word_count: int = field(init=False)
    char_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.char_count = len(self.text)
        self.word_count = len(self.text.split()) if self.text.strip() else 0


@dataclass
class PDFAnalysisResult:
    """Result of analyzing a PDF for scanned vs native pages."""

    total_pages: int
    scanned_pages: int
    native_pages: int
    classification: ExtractionMethod
    scanned_page_numbers: list[int] = field(default_factory=list)

    @property
    def scanned_ratio(self) -> float:
        """Return ratio of scanned pages to total pages."""
        if self.total_pages == 0:
            return 0.0
        return self.scanned_pages / self.total_pages


@dataclass
class PDFExtractionResult:
    """Complete result of PDF text extraction."""

    book_id: str
    publisher_id: str
    book_name: str
    total_pages: int
    pages: list[PageText]
    method: ExtractionMethod
    scanned_page_count: int
    native_page_count: int
    total_word_count: int = field(init=False)
    total_char_count: int = field(init=False)
    extracted_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        self.total_word_count = sum(p.word_count for p in self.pages)
        self.total_char_count = sum(p.char_count for p in self.pages)

    def to_metadata_dict(self) -> dict[str, Any]:
        """Convert to dictionary for metadata.json storage."""
        return {
            "book_id": self.book_id,
            "publisher_id": self.publisher_id,
            "book_name": self.book_name,
            "extraction_method": self.method.value,
            "total_pages": self.total_pages,
            "scanned_pages": self.scanned_page_count,
            "native_pages": self.native_page_count,
            "total_word_count": self.total_word_count,
            "total_char_count": self.total_char_count,
            "extracted_at": self.extracted_at.isoformat(),
        }
