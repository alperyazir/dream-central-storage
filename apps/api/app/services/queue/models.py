"""Queue infrastructure models for AI processing jobs."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class ProcessingStatus(str, Enum):
    """Status of a processing job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some steps succeeded, others failed
    CANCELLED = "cancelled"


class ProcessingJobType(str, Enum):
    """Type of processing job."""

    FULL = "full"  # All processing steps
    TEXT_ONLY = "text_only"  # PDF extraction only
    VOCABULARY_ONLY = "vocabulary_only"
    AUDIO_ONLY = "audio_only"


class JobPriority(str, Enum):
    """Priority level for job execution."""

    HIGH = "high"  # Admin re-processing, urgent
    NORMAL = "normal"  # Standard auto-processing
    LOW = "low"  # Bulk/batch processing


@dataclass
class ProcessingJob:
    """Represents an AI processing job for a book."""

    job_id: str
    book_id: str
    publisher_id: str
    job_type: ProcessingJobType = ProcessingJobType.FULL
    status: ProcessingStatus = ProcessingStatus.QUEUED
    priority: JobPriority = JobPriority.NORMAL
    progress: int = 0  # 0-100 percentage
    current_step: str = ""  # Current processing step
    error_message: str | None = None
    retry_count: int = 0
    created_at: datetime = field(default_factory=_utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict = field(default_factory=dict)  # Additional job context


@dataclass
class QueueStats:
    """Statistics about the processing queue."""

    total_jobs: int
    queued_jobs: int
    processing_jobs: int
    completed_jobs: int
    failed_jobs: int
    active_workers: int


# Processing stages with weight percentages
PROCESSING_STAGES = {
    "text_extraction": 20,  # PDF -> text files
    "segmentation": 15,  # Text -> modules
    "topic_analysis": 20,  # AI topic extraction
    "vocabulary": 20,  # AI vocabulary extraction
    "audio_generation": 25,  # TTS for vocabulary
}


class QueueError(Exception):
    """Base exception for queue errors."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class JobNotFoundError(QueueError):
    """Raised when a job is not found in the queue."""

    def __init__(self, job_id: str):
        super().__init__(f"Job not found: {job_id}", {"job_id": job_id})


class JobAlreadyExistsError(QueueError):
    """Raised when trying to create a duplicate job."""

    def __init__(self, book_id: str):
        super().__init__(
            f"Job already exists for book: {book_id}", {"book_id": book_id}
        )


class QueueConnectionError(QueueError):
    """Raised when Redis connection fails."""

    pass
