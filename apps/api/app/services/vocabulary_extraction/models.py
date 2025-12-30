"""Vocabulary extraction data models and exceptions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class PartOfSpeech(str, Enum):
    """Parts of speech for vocabulary words."""

    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PRONOUN = "pronoun"
    PREPOSITION = "preposition"
    CONJUNCTION = "conjunction"
    INTERJECTION = "interjection"
    ARTICLE = "article"
    DETERMINER = "determiner"
    UNKNOWN = "unknown"


# =============================================================================
# Exceptions
# =============================================================================


class VocabularyExtractionError(Exception):
    """Base exception for vocabulary extraction errors."""

    def __init__(
        self, message: str, book_id: str, details: dict[str, Any] | None = None
    ) -> None:
        self.message = message
        self.book_id = book_id
        self.details = details or {}
        super().__init__(f"[{book_id}] {message}")


class LLMExtractionError(VocabularyExtractionError):
    """Raised when LLM vocabulary extraction fails."""

    def __init__(
        self,
        book_id: str,
        module_id: int,
        reason: str,
        provider: str | None = None,
    ) -> None:
        details = {"module_id": module_id, "reason": reason}
        if provider:
            details["provider"] = provider
        super().__init__(
            f"LLM vocabulary extraction failed for module {module_id}: {reason}",
            book_id,
            details,
        )
        self.module_id = module_id
        self.reason = reason
        self.provider = provider


class NoModulesFoundError(VocabularyExtractionError):
    """Raised when no modules are found for vocabulary extraction."""

    def __init__(self, book_id: str, path: str) -> None:
        super().__init__(
            f"No modules found at: {path}",
            book_id,
            {"path": path},
        )
        self.path = path


class InvalidLLMResponseError(VocabularyExtractionError):
    """Raised when LLM response cannot be parsed."""

    def __init__(
        self,
        book_id: str,
        module_id: int,
        response: str,
        parse_error: str,
    ) -> None:
        super().__init__(
            f"Invalid LLM response for module {module_id}: {parse_error}",
            book_id,
            {"module_id": module_id, "response": response[:500], "parse_error": parse_error},
        )
        self.module_id = module_id
        self.response = response
        self.parse_error = parse_error


class DuplicateVocabularyError(VocabularyExtractionError):
    """Raised when duplicate vocabulary handling fails."""

    def __init__(self, book_id: str, word: str, module_ids: list[int]) -> None:
        super().__init__(
            f"Duplicate vocabulary word '{word}' found in modules: {module_ids}",
            book_id,
            {"word": word, "module_ids": module_ids},
        )
        self.word = word
        self.module_ids = module_ids


# =============================================================================
# Data Models
# =============================================================================


def _slugify(text: str) -> str:
    """Create a URL-safe slug from text."""
    import re
    # Convert to lowercase
    slug = text.lower()
    # Replace spaces and special chars with underscores
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    # Remove leading/trailing underscores
    slug = slug.strip("_")
    return slug


@dataclass
class VocabularyWord:
    """A single vocabulary word with all metadata."""

    word: str
    id: str = ""  # Slugified word ID
    translation: str = ""
    definition: str = ""
    part_of_speech: str = ""
    level: str = ""  # CEFR level: A1, A2, B1, B2, C1, C2
    example: str = ""
    module_id: int = 0
    page: int = 0
    audio: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate ID from word if not provided."""
        if not self.id and self.word:
            self.id = _slugify(self.word)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "id": self.id,
            "word": self.word,
            "translation": self.translation,
            "definition": self.definition,
            "part_of_speech": self.part_of_speech,
            "level": self.level,
            "example": self.example,
            "module_id": self.module_id,
            "page": self.page,
            "audio": self.audio,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VocabularyWord:
        """Create VocabularyWord from dictionary."""
        return cls(
            id=data.get("id", ""),
            word=data.get("word", ""),
            translation=data.get("translation", ""),
            definition=data.get("definition", ""),
            part_of_speech=data.get("part_of_speech", ""),
            level=data.get("level", ""),
            example=data.get("example", ""),
            module_id=data.get("module_id", 0),
            page=data.get("page", 0),
            audio=data.get("audio", {}),
        )


@dataclass
class ModuleVocabularyResult:
    """Result of vocabulary extraction for a single module."""

    module_id: int
    module_title: str = ""
    words: list[VocabularyWord] = field(default_factory=list)
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    llm_provider: str = ""
    tokens_used: int = 0
    success: bool = True
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "module_id": self.module_id,
            "module_title": self.module_title,
            "word_count": len(self.words),
            "words": [w.to_dict() for w in self.words],
            "extracted_at": self.extracted_at.isoformat(),
            "llm_provider": self.llm_provider,
            "tokens_used": self.tokens_used,
            "success": self.success,
            "error_message": self.error_message,
        }

    @property
    def vocabulary_ids(self) -> list[str]:
        """Get list of vocabulary word IDs for this module."""
        return [w.id for w in self.words]


@dataclass
class BookVocabularyResult:
    """Result of vocabulary extraction for an entire book."""

    book_id: str
    publisher_id: str
    book_name: str
    language: str = "en"
    translation_language: str = "tr"
    words: list[VocabularyWord] = field(default_factory=list)
    module_results: list[ModuleVocabularyResult] = field(default_factory=list)
    extracted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success_count: int = 0
    failure_count: int = 0

    def __post_init__(self) -> None:
        """Calculate derived fields after initialization."""
        self._calculate_aggregates()

    def _calculate_aggregates(self) -> None:
        """Calculate aggregate statistics from module results."""
        if not self.module_results:
            return

        self.success_count = sum(1 for r in self.module_results if r.success)
        self.failure_count = sum(1 for r in self.module_results if not r.success)

    @property
    def total_words(self) -> int:
        """Get total number of unique vocabulary words."""
        return len(self.words)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage (vocabulary.json format)."""
        return {
            "language": self.language,
            "translation_language": self.translation_language,
            "total_words": self.total_words,
            "words": [w.to_dict() for w in self.words],
            "extracted_at": self.extracted_at.isoformat(),
        }

    def to_metadata_dict(self) -> dict[str, Any]:
        """Convert to metadata dictionary for tracking."""
        return {
            "book_id": self.book_id,
            "publisher_id": self.publisher_id,
            "book_name": self.book_name,
            "language": self.language,
            "translation_language": self.translation_language,
            "total_words": self.total_words,
            "module_count": len(self.module_results),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "extracted_at": self.extracted_at.isoformat(),
            "modules": [r.to_dict() for r in self.module_results],
        }
