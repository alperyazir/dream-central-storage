"""Topic analysis data models and exceptions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CEFRLevel(str, Enum):
    """Common European Framework of Reference for Languages levels."""

    A1 = "A1"  # Beginner
    A2 = "A2"  # Elementary
    B1 = "B1"  # Intermediate
    B2 = "B2"  # Upper Intermediate
    C1 = "C1"  # Advanced
    C2 = "C2"  # Proficient


class TargetSkill(str, Enum):
    """Target language skills."""

    READING = "reading"
    WRITING = "writing"
    SPEAKING = "speaking"
    LISTENING = "listening"


class DetectedLanguage(str, Enum):
    """Supported detected languages."""

    ENGLISH = "en"
    TURKISH = "tr"
    BILINGUAL = "bilingual"
    UNKNOWN = "unknown"


# =============================================================================
# Exceptions
# =============================================================================


class TopicAnalysisError(Exception):
    """Base exception for topic analysis errors."""

    def __init__(
        self, message: str, book_id: str, details: dict[str, Any] | None = None
    ) -> None:
        self.message = message
        self.book_id = book_id
        self.details = details or {}
        super().__init__(f"[{book_id}] {message}")


class LLMAnalysisError(TopicAnalysisError):
    """Raised when LLM analysis fails."""

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
            f"LLM analysis failed for module {module_id}: {reason}",
            book_id,
            details,
        )
        self.module_id = module_id
        self.reason = reason
        self.provider = provider


class NoModulesFoundError(TopicAnalysisError):
    """Raised when no modules are found for analysis."""

    def __init__(self, book_id: str, path: str) -> None:
        super().__init__(
            f"No modules found at: {path}",
            book_id,
            {"path": path},
        )
        self.path = path


class InvalidLLMResponseError(TopicAnalysisError):
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


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class TopicResult:
    """Result of topic analysis for a single module."""

    topics: list[str] = field(default_factory=list)
    grammar_points: list[str] = field(default_factory=list)
    difficulty: str = ""  # CEFR level: A1, A2, B1, B2, C1, C2
    language: str = ""  # en, tr, bilingual
    target_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "topics": self.topics,
            "grammar_points": self.grammar_points,
            "difficulty": self.difficulty,
            "language": self.language,
            "target_skills": self.target_skills,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TopicResult:
        """Create TopicResult from dictionary."""
        return cls(
            topics=data.get("topics", []),
            grammar_points=data.get("grammar_points", []),
            difficulty=data.get("difficulty", ""),
            language=data.get("language", ""),
            target_skills=data.get("target_skills", []),
        )

    @classmethod
    def empty(cls) -> TopicResult:
        """Create empty TopicResult for fallback."""
        return cls()


@dataclass
class ModuleAnalysisResult:
    """Result of topic analysis for a single module with metadata."""

    module_id: int
    module_title: str
    topic_result: TopicResult
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    llm_provider: str = ""
    tokens_used: int = 0
    success: bool = True
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "module_id": self.module_id,
            "module_title": self.module_title,
            "topic_result": self.topic_result.to_dict(),
            "analyzed_at": self.analyzed_at.isoformat(),
            "llm_provider": self.llm_provider,
            "tokens_used": self.tokens_used,
            "success": self.success,
            "error_message": self.error_message,
        }


@dataclass
class BookAnalysisResult:
    """Result of topic analysis for an entire book."""

    book_id: str
    publisher_id: str
    book_name: str
    module_results: list[ModuleAnalysisResult] = field(default_factory=list)
    primary_language: str = ""
    difficulty_range: list[str] = field(default_factory=list)
    total_topics: int = 0
    total_grammar_points: int = 0
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    success_count: int = 0
    failure_count: int = 0

    def __post_init__(self) -> None:
        """Calculate derived fields after initialization."""
        self._calculate_aggregates()

    def _calculate_aggregates(self) -> None:
        """Calculate aggregate statistics from module results."""
        if not self.module_results:
            return

        # Count successes and failures
        self.success_count = sum(1 for r in self.module_results if r.success)
        self.failure_count = sum(1 for r in self.module_results if not r.success)

        # Aggregate topics and grammar points
        all_topics = set()
        all_grammar_points = set()
        languages = []
        difficulties = []

        for result in self.module_results:
            if result.success:
                all_topics.update(result.topic_result.topics)
                all_grammar_points.update(result.topic_result.grammar_points)
                if result.topic_result.language:
                    languages.append(result.topic_result.language)
                if result.topic_result.difficulty:
                    difficulties.append(result.topic_result.difficulty)

        self.total_topics = len(all_topics)
        self.total_grammar_points = len(all_grammar_points)

        # Determine primary language
        if languages:
            from collections import Counter
            lang_counts = Counter(languages)
            self.primary_language = lang_counts.most_common(1)[0][0]

        # Determine difficulty range
        if difficulties:
            unique_difficulties = sorted(set(difficulties), key=lambda x: ["A1", "A2", "B1", "B2", "C1", "C2"].index(x) if x in ["A1", "A2", "B1", "B2", "C1", "C2"] else 99)
            self.difficulty_range = unique_difficulties

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            "book_id": self.book_id,
            "publisher_id": self.publisher_id,
            "book_name": self.book_name,
            "module_count": len(self.module_results),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "primary_language": self.primary_language,
            "difficulty_range": self.difficulty_range,
            "total_topics": self.total_topics,
            "total_grammar_points": self.total_grammar_points,
            "analyzed_at": self.analyzed_at.isoformat(),
            "modules": [r.to_dict() for r in self.module_results],
        }
