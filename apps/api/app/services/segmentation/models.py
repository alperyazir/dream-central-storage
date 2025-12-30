"""Segmentation data models and exceptions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SegmentationMethod(str, Enum):
    """Method used for text segmentation."""

    HEADER_BASED = "header_based"  # Detected from headers/titles
    TOC_BASED = "toc_based"  # Parsed from table of contents
    AI_ASSISTED = "ai_assisted"  # AI identified segments
    MANUAL = "manual"  # Admin-defined segments
    SINGLE_MODULE = "single_module"  # Entire book as one module
    PAGE_SPLIT = "page_split"  # Split by page count


# =============================================================================
# Exceptions
# =============================================================================


class SegmentationError(Exception):
    """Base exception for segmentation errors."""

    def __init__(
        self, message: str, book_id: str, details: dict[str, Any] | None = None
    ) -> None:
        self.message = message
        self.book_id = book_id
        self.details = details or {}
        super().__init__(f"[{book_id}] {message}")


class NoTextFoundError(SegmentationError):
    """Raised when no extracted text is found for segmentation."""

    def __init__(self, book_id: str, path: str) -> None:
        super().__init__(f"No extracted text found at: {path}", book_id, {"path": path})
        self.path = path


class InvalidModuleDefinitionError(SegmentationError):
    """Raised when manual module definition is invalid."""

    def __init__(self, book_id: str, reason: str) -> None:
        super().__init__(
            f"Invalid module definition: {reason}", book_id, {"reason": reason}
        )
        self.reason = reason


class SegmentationLimitError(SegmentationError):
    """Raised when segmentation exceeds limits."""

    def __init__(self, book_id: str, count: int, max_count: int) -> None:
        super().__init__(
            f"Too many modules: {count} exceeds limit of {max_count}",
            book_id,
            {"count": count, "max_count": max_count},
        )
        self.count = count
        self.max_count = max_count


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class ModuleBoundary:
    """Detected boundary for a module."""

    title: str
    start_page: int
    confidence: float = 1.0  # 0.0 to 1.0, how confident the detection is


@dataclass
class Module:
    """Represents a segmented module/chapter of a book."""

    module_id: int
    title: str
    pages: list[int]
    start_page: int
    end_page: int
    text: str = ""
    word_count: int = field(init=False)
    char_count: int = field(init=False)
    # Fields populated by later stories
    topics: list[str] = field(default_factory=list)
    vocabulary_ids: list[str] = field(default_factory=list)
    language: str = ""
    difficulty: str = ""

    def __post_init__(self) -> None:
        self.word_count = len(self.text.split()) if self.text.strip() else 0
        self.char_count = len(self.text)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "module_id": self.module_id,
            "title": self.title,
            "pages": self.pages,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "text": self.text,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "topics": self.topics,
            "vocabulary_ids": self.vocabulary_ids,
            "language": self.language,
            "difficulty": self.difficulty,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Module:
        """Create Module from dictionary."""
        module = cls(
            module_id=data["module_id"],
            title=data["title"],
            pages=data["pages"],
            start_page=data["start_page"],
            end_page=data["end_page"],
            text=data.get("text", ""),
        )
        module.topics = data.get("topics", [])
        module.vocabulary_ids = data.get("vocabulary_ids", [])
        module.language = data.get("language", "")
        module.difficulty = data.get("difficulty", "")
        return module


@dataclass
class SegmentationResult:
    """Complete result of book segmentation."""

    book_id: str
    publisher_id: str
    book_name: str
    total_pages: int
    modules: list[Module]
    method: SegmentationMethod
    segmented_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    @property
    def module_count(self) -> int:
        """Return number of modules."""
        return len(self.modules)

    @property
    def total_word_count(self) -> int:
        """Return total word count across all modules."""
        return sum(m.word_count for m in self.modules)

    def to_metadata_dict(self) -> dict[str, Any]:
        """Convert to dictionary for metadata.json storage."""
        return {
            "book_id": self.book_id,
            "publisher_id": self.publisher_id,
            "book_name": self.book_name,
            "total_pages": self.total_pages,
            "segmentation_method": self.method.value,
            "module_count": self.module_count,
            "total_word_count": self.total_word_count,
            "modules": [
                {
                    "module_id": m.module_id,
                    "title": m.title,
                    "pages": m.pages,
                    "word_count": m.word_count,
                }
                for m in self.modules
            ],
            "segmented_at": self.segmented_at.isoformat(),
        }


@dataclass
class ManualModuleDefinition:
    """Manual module definition from admin/config."""

    title: str
    start_page: int
    end_page: int

    def validate(self, total_pages: int) -> list[str]:
        """Validate the definition, return list of errors."""
        errors = []
        if self.start_page < 1:
            errors.append(f"start_page must be >= 1, got {self.start_page}")
        if self.end_page < self.start_page:
            errors.append(
                f"end_page ({self.end_page}) must be >= start_page ({self.start_page})"
            )
        if self.end_page > total_pages:
            errors.append(
                f"end_page ({self.end_page}) exceeds total pages ({total_pages})"
            )
        if not self.title.strip():
            errors.append("title cannot be empty")
        return errors
