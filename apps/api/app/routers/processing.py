"""API endpoints for AI processing operations."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token, verify_api_key_from_db
from app.db import get_db
from app.repositories.book import BookRepository
from app.repositories.user import UserRepository
from app.schemas.processing import (
    CleanupStatsResponse,
    ProcessingJobResponse,
    ProcessingStatusResponse,
    ProcessingTriggerRequest,
)
from app.services import get_minio_client
from app.services.ai_data import get_ai_data_cleanup_manager
from app.services.queue.models import (
    JobAlreadyExistsError,
    JobPriority,
)
from app.services.queue.service import get_queue_service

router = APIRouter(prefix="/books", tags=["AI Processing"])
_bearer_scheme = HTTPBearer(auto_error=True)
_book_repository = BookRepository()
_user_repository = UserRepository()
logger = logging.getLogger(__name__)

# Rate limiting constants
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
MAX_JOBS_PER_PUBLISHER = 10


def _require_auth(credentials: HTTPAuthorizationCredentials, db: Session) -> int:
    """Validate JWT token or API key and return user ID or -1 for API key auth."""
    token = credentials.credentials

    # Try JWT first
    try:
        payload = decode_access_token(token, settings=get_settings())
        subject = payload.get("sub")
        if subject is not None:
            try:
                user_id = int(subject)
                user = _user_repository.get(db, user_id)
                if user is not None:
                    return user_id
            except (TypeError, ValueError):
                pass
    except ValueError:
        pass  # JWT failed, try API key

    # Try API key
    api_key_info = verify_api_key_from_db(token, db)
    if api_key_info is not None:
        return -1  # API key authentication

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )


async def _check_rate_limit(publisher_id: int) -> tuple[bool, int]:
    """Check if publisher has exceeded rate limit.

    Args:
        publisher_id: Publisher ID to check

    Returns:
        Tuple of (is_allowed, retry_after_seconds)
    """
    settings = get_settings()
    from app.services.queue.redis import get_redis_connection

    redis_conn = await get_redis_connection(url=settings.redis_url)
    key = f"dcs:rate_limit:{publisher_id}"

    current = await redis_conn.client.incr(key)
    if current == 1:
        await redis_conn.client.expire(key, RATE_LIMIT_WINDOW)

    ttl = await redis_conn.client.ttl(key)
    if ttl < 0:
        ttl = RATE_LIMIT_WINDOW

    if current > MAX_JOBS_PER_PUBLISHER:
        return False, ttl
    return True, 0


def _book_has_content(book) -> bool:
    """Check if book has content in MinIO storage."""
    settings = get_settings()
    client = get_minio_client(settings)
    prefix = f"{book.publisher}/books/{book.book_name}/"

    try:
        objects = list(
            client.list_objects(
                settings.minio_publishers_bucket,
                prefix=prefix,
                recursive=False,
            )
        )
        return len(objects) > 0
    except Exception as e:
        logger.error("Failed to check book content: %s", e)
        return False


@router.post(
    "/{book_id}/process-ai",
    response_model=ProcessingJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_processing(
    book_id: int,
    payload: ProcessingTriggerRequest,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> ProcessingJobResponse:
    """Trigger AI processing for a book.

    Queues a new processing job for the specified book. The job will extract
    text, segment content, analyze topics, extract vocabulary, and generate
    audio pronunciations.

    Args:
        book_id: ID of the book to process
        payload: Processing options (job_type, priority, admin_override)

    Returns:
        ProcessingJobResponse with job details

    Raises:
        404: Book not found
        400: Book has no content to process
        409: Active processing job already exists for book
        429: Rate limit exceeded
    """
    user_id = _require_auth(credentials, db)

    # Validate book exists
    book = _book_repository.get_by_id(db, book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    # Validate book has content
    if not _book_has_content(book):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book has no content to process",
        )

    # Check rate limit (skip if admin_override)
    if not payload.admin_override:
        allowed, retry_after = await _check_rate_limit(book.publisher_id)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded for publisher"},
                headers={"Retry-After": str(retry_after)},
            )

    # Validate admin_override and priority
    priority = payload.priority
    if payload.admin_override or priority == JobPriority.HIGH:
        # For HIGH priority or admin_override, require authenticated user (not API key)
        if user_id == -1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin override and HIGH priority require user authentication",
            )

    # Enqueue processing job
    queue_service = await get_queue_service()
    try:
        job = await queue_service.enqueue_job(
            book_id=str(book.id),
            publisher_id=str(book.publisher_id),
            job_type=payload.job_type,
            priority=priority,
            metadata={"book_name": book.book_name, "publisher": book.publisher},
        )
    except JobAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active processing job already exists for this book",
        )

    logger.info(
        "Triggered AI processing for book %s (job_id=%s, type=%s, priority=%s)",
        book_id,
        job.job_id,
        job.job_type.value,
        job.priority.value,
    )

    return ProcessingJobResponse(
        job_id=job.job_id,
        book_id=job.book_id,
        publisher_id=job.publisher_id,
        job_type=job.job_type,
        status=job.status,
        priority=job.priority,
        progress=job.progress,
        current_step=job.current_step,
        error_message=job.error_message,
        retry_count=job.retry_count,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.get(
    "/{book_id}/process-ai/status",
    response_model=ProcessingStatusResponse,
)
async def get_processing_status(
    book_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> ProcessingStatusResponse:
    """Get the current AI processing status for a book.

    Returns the most recent processing job status for the specified book.

    Args:
        book_id: ID of the book

    Returns:
        ProcessingStatusResponse with job status and progress

    Raises:
        404: Book not found or no processing jobs exist
    """
    _require_auth(credentials, db)

    # Validate book exists
    book = _book_repository.get_by_id(db, book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    # Get most recent job for this book
    queue_service = await get_queue_service()
    jobs = await queue_service.list_jobs(book_id=str(book.id), limit=1)

    if not jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No processing jobs found for this book",
        )

    job = jobs[0]
    return ProcessingStatusResponse(
        job_id=job.job_id,
        book_id=job.book_id,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.delete(
    "/{book_id}/ai-data",
    response_model=CleanupStatsResponse,
)
async def delete_ai_data(
    book_id: int,
    reprocess: bool = Query(
        default=False,
        description="Trigger reprocessing after cleanup",
    ),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> CleanupStatsResponse:
    """Delete AI-generated data for a book.

    Removes all data under /ai-data/ for the specified book, including
    extracted text, modules, vocabulary, and audio files.

    Optionally triggers reprocessing after cleanup.

    Args:
        book_id: ID of the book
        reprocess: If True, queue a new processing job after cleanup

    Returns:
        CleanupStatsResponse with deletion statistics

    Raises:
        404: Book not found
    """
    _require_auth(credentials, db)

    # Validate book exists
    book = _book_repository.get_by_id(db, book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )

    # Cleanup AI data
    cleanup_manager = get_ai_data_cleanup_manager()
    stats = cleanup_manager.cleanup_all(
        publisher_id=str(book.publisher_id),
        book_id=str(book.id),
        book_name=book.book_name,
    )

    logger.info(
        "Deleted AI data for book %s: %d files removed",
        book_id,
        stats.total_deleted,
    )

    # Optionally trigger reprocessing
    if reprocess and _book_has_content(book):
        queue_service = await get_queue_service()
        try:
            job = await queue_service.enqueue_job(
                book_id=str(book.id),
                publisher_id=str(book.publisher_id),
                metadata={"book_name": book.book_name, "publisher": book.publisher},
            )
            logger.info(
                "Triggered reprocessing for book %s (job_id=%s)",
                book_id,
                job.job_id,
            )
        except JobAlreadyExistsError:
            logger.warning(
                "Skipped reprocessing for book %s: active job exists",
                book_id,
            )

    return CleanupStatsResponse(
        total_deleted=stats.total_deleted,
        text_deleted=stats.text_deleted,
        modules_deleted=stats.modules_deleted,
        audio_deleted=stats.audio_deleted,
        vocabulary_deleted=stats.vocabulary_deleted,
        metadata_deleted=stats.metadata_deleted,
        errors=stats.errors,
    )
