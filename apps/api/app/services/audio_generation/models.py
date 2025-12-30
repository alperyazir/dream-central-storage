"""Audio generation data models and exceptions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# =============================================================================
# Exceptions
# =============================================================================


class AudioGenerationError(Exception):
    """Base exception for audio generation errors."""

    def __init__(
        self, message: str, book_id: str, details: dict[str, Any] | None = None
    ) -> None:
        self.message = message
        self.book_id = book_id
        self.details = details or {}
        super().__init__(f"[{book_id}] {message}")


class TTSError(AudioGenerationError):
    """Raised when TTS synthesis fails."""

    def __init__(
        self,
        book_id: str,
        word: str,
        language: str,
        reason: str,
        provider: str | None = None,
    ) -> None:
        details = {"word": word, "language": language, "reason": reason}
        if provider:
            details["provider"] = provider
        super().__init__(
            f"TTS failed for word '{word}' ({language}): {reason}",
            book_id,
            details,
        )
        self.word = word
        self.language = language
        self.reason = reason
        self.provider = provider


class StorageError(AudioGenerationError):
    """Raised when audio storage operations fail."""

    def __init__(
        self,
        book_id: str,
        operation: str,
        path: str,
        reason: str,
    ) -> None:
        super().__init__(
            f"Storage {operation} failed for '{path}': {reason}",
            book_id,
            {"operation": operation, "path": path, "reason": reason},
        )
        self.operation = operation
        self.path = path
        self.reason = reason


class NoVocabularyFoundError(AudioGenerationError):
    """Raised when no vocabulary is found for audio generation."""

    def __init__(self, book_id: str, path: str) -> None:
        super().__init__(
            f"No vocabulary found at: {path}",
            book_id,
            {"path": path},
        )
        self.path = path


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class AudioFile:
    """Represents a generated audio file."""

    word_id: str
    word: str
    language: str
    file_path: str  # Relative path within ai-data/
    duration_ms: int | None = None
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "word_id": self.word_id,
            "word": self.word,
            "language": self.language,
            "file_path": self.file_path,
            "duration_ms": self.duration_ms,
            "generated_at": self.generated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudioFile:
        """Create AudioFile from dictionary."""
        generated_at = data.get("generated_at")
        if isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)
        elif generated_at is None:
            generated_at = datetime.now(timezone.utc)

        return cls(
            word_id=data.get("word_id", ""),
            word=data.get("word", ""),
            language=data.get("language", ""),
            file_path=data.get("file_path", ""),
            duration_ms=data.get("duration_ms"),
            generated_at=generated_at,
        )


@dataclass
class WordAudioResult:
    """Result of audio generation for a single word."""

    word_id: str
    word: str
    language: str
    success: bool = True
    audio_file: AudioFile | None = None
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "word_id": self.word_id,
            "word": self.word,
            "language": self.language,
            "success": self.success,
            "audio_file": self.audio_file.to_dict() if self.audio_file else None,
            "error_message": self.error_message,
        }


@dataclass
class BookAudioResult:
    """Result of audio generation for an entire book's vocabulary."""

    book_id: str
    publisher_id: str
    book_name: str
    language: str = "en"
    translation_language: str = "tr"
    total_words: int = 0
    generated_count: int = 0
    failed_count: int = 0
    word_results: list[WordAudioResult] = field(default_factory=list)
    audio_files: list[AudioFile] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Calculate derived fields after initialization."""
        self._calculate_aggregates()

    def _calculate_aggregates(self) -> None:
        """Calculate aggregate statistics from word results."""
        if not self.word_results:
            return

        self.generated_count = sum(1 for r in self.word_results if r.success)
        self.failed_count = sum(1 for r in self.word_results if not r.success)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "book_id": self.book_id,
            "publisher_id": self.publisher_id,
            "book_name": self.book_name,
            "language": self.language,
            "translation_language": self.translation_language,
            "total_words": self.total_words,
            "generated_count": self.generated_count,
            "failed_count": self.failed_count,
            "audio_files_count": len(self.audio_files),
            "generated_at": self.generated_at.isoformat(),
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
            "generated_count": self.generated_count,
            "failed_count": self.failed_count,
            "audio_files": [af.to_dict() for af in self.audio_files],
            "word_results": [wr.to_dict() for wr in self.word_results],
            "generated_at": self.generated_at.isoformat(),
        }
