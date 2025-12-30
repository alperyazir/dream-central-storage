"""Worker task definitions for arq."""

import logging
from typing import Any

from arq import ArqRedis

from app.core.config import get_settings
from app.services.queue.models import (
    ProcessingJobType,
    ProcessingStatus,
    PROCESSING_STAGES,
    QueueError,
)
from app.services.queue.repository import JobRepository
from app.services.queue.redis import get_redis_connection
from app.services.queue.service import ProgressReporter

# Import PDF extraction service for text_extraction stage
from app.services.pdf import get_extraction_service, get_ai_storage

# Import segmentation service for segmentation stage
from app.services.segmentation import get_segmentation_service, get_module_storage

logger = logging.getLogger(__name__)


async def process_book_task(
    ctx: dict[str, Any],
    job_id: str,
    book_id: str,
    publisher_id: str,
    job_type: str,
    book_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Main entry point for book processing.

    This task orchestrates the full book processing pipeline including:
    - Text extraction from PDF
    - Content segmentation
    - AI topic analysis
    - Vocabulary extraction
    - Audio generation

    Args:
        ctx: arq context with Redis connection
        job_id: Processing job ID
        book_id: Book to process
        publisher_id: Publisher owning the book
        job_type: Type of processing (full, text_only, etc.)
        book_name: Book folder name (required for storage path)
        metadata: Additional job metadata

    Returns:
        Result dict with status and any output data

    Raises:
        QueueError: If processing fails after all retries
    """
    settings = get_settings()
    redis_conn = await get_redis_connection(url=settings.redis_url)
    repository = JobRepository(
        redis_client=redis_conn.client,
        job_ttl_seconds=settings.queue_job_ttl_seconds,
    )
    progress = ProgressReporter(repository, job_id)

    # Merge metadata with book_name
    job_metadata = metadata or {}
    if book_name:
        job_metadata["book_name"] = book_name

    logger.info(
        "Starting processing job %s for book %s (type: %s)",
        job_id,
        book_id,
        job_type,
    )

    # Update job status to processing
    await repository.update_job_status(job_id, ProcessingStatus.PROCESSING)

    job_type_enum = ProcessingJobType(job_type)
    stages_to_run = _get_stages_for_job_type(job_type_enum)
    errors: list[dict] = []
    completed_stages: list[str] = []
    stage_results: dict[str, Any] = {}  # Store results for passing between stages

    try:
        for stage in stages_to_run:
            try:
                result = await _run_processing_stage(
                    stage=stage,
                    job_id=job_id,
                    book_id=book_id,
                    publisher_id=publisher_id,
                    progress=progress,
                    metadata=job_metadata,
                    stage_results=stage_results,
                )
                if result:
                    stage_results[stage] = result
                completed_stages.append(stage)
                await progress.report_step_complete(stage)

            except Exception as stage_error:
                logger.error(
                    "Stage %s failed for job %s: %s",
                    stage,
                    job_id,
                    stage_error,
                )
                errors.append({
                    "stage": stage,
                    "error": str(stage_error),
                })

                # Continue on non-critical errors for partial completion
                if not _is_critical_stage(stage):
                    logger.warning(
                        "Continuing after non-critical stage failure: %s",
                        stage,
                    )
                    continue

                # Critical stage failed - abort
                raise

        # All stages completed
        if errors:
            # Some non-critical stages failed
            await repository.update_job_status(
                job_id,
                ProcessingStatus.PARTIAL,
                error_message=f"Partial completion: {len(errors)} stage(s) failed",
            )
            logger.warning(
                "Job %s completed partially with %d error(s)",
                job_id,
                len(errors),
            )
            return {
                "status": "partial",
                "completed_stages": completed_stages,
                "errors": errors,
            }

        await repository.update_job_status(job_id, ProcessingStatus.COMPLETED)
        logger.info("Job %s completed successfully", job_id)
        return {
            "status": "completed",
            "completed_stages": completed_stages,
        }

    except Exception as e:
        logger.error("Job %s failed: %s", job_id, e)
        await repository.update_job_status(
            job_id,
            ProcessingStatus.FAILED,
            error_message=str(e),
        )
        raise QueueError(f"Processing failed: {e}") from e


def _get_stages_for_job_type(job_type: ProcessingJobType) -> list[str]:
    """Get processing stages for a job type.

    Args:
        job_type: Type of processing job

    Returns:
        List of stage names to execute
    """
    all_stages = list(PROCESSING_STAGES.keys())

    if job_type == ProcessingJobType.FULL:
        return all_stages
    elif job_type == ProcessingJobType.TEXT_ONLY:
        return ["text_extraction", "segmentation"]
    elif job_type == ProcessingJobType.VOCABULARY_ONLY:
        return ["vocabulary"]
    elif job_type == ProcessingJobType.AUDIO_ONLY:
        return ["audio_generation"]

    return all_stages


def _is_critical_stage(stage: str) -> bool:
    """Check if a stage failure should abort processing.

    Args:
        stage: Stage name

    Returns:
        True if stage is critical
    """
    # Text extraction and segmentation are critical - can't proceed without them
    critical_stages = {"text_extraction", "segmentation"}
    return stage in critical_stages


async def _run_processing_stage(
    stage: str,
    job_id: str,
    book_id: str,
    publisher_id: str,
    progress: ProgressReporter,
    metadata: dict[str, Any] | None = None,
    stage_results: dict[str, Any] | None = None,
) -> Any:
    """Run a single processing stage.

    Args:
        stage: Stage name
        job_id: Job ID
        book_id: Book ID
        publisher_id: Publisher ID
        progress: Progress reporter
        metadata: Job metadata (contains book_name, etc.)
        stage_results: Results from previous stages

    Returns:
        Stage result data (if any)
    """
    logger.info("Running stage %s for job %s", stage, job_id)
    metadata = metadata or {}
    stage_results = stage_results or {}

    # Report initial progress for stage
    await progress.report_progress(stage, 0)

    if stage == "text_extraction":
        return await _run_text_extraction(
            job_id=job_id,
            book_id=book_id,
            publisher_id=publisher_id,
            book_name=metadata.get("book_name", ""),
            progress=progress,
        )

    if stage == "segmentation":
        return await _run_segmentation(
            job_id=job_id,
            book_id=book_id,
            publisher_id=publisher_id,
            book_name=metadata.get("book_name", ""),
            progress=progress,
            text_extraction_result=stage_results.get("text_extraction"),
        )

    # Placeholder for other stages (to be implemented in future stories)
    # - topic_analysis: LLM service
    # - vocabulary: LLM service
    # - audio_generation: TTS service

    await progress.report_progress(stage, 50)
    await progress.report_progress(stage, 100)

    logger.info("Completed stage %s for job %s", stage, job_id)
    return None


async def _run_text_extraction(
    job_id: str,
    book_id: str,
    publisher_id: str,
    book_name: str,
    progress: ProgressReporter,
) -> dict[str, Any]:
    """Run text extraction stage.

    Extracts text from the book's PDF and stores it in ai-data.

    Args:
        job_id: Job ID
        book_id: Book ID
        publisher_id: Publisher ID
        book_name: Book folder name
        progress: Progress reporter

    Returns:
        Extraction result data

    Raises:
        QueueError: If book_name is missing or extraction fails
    """
    if not book_name:
        raise QueueError(
            "book_name is required for text extraction",
            {"job_id": job_id, "book_id": book_id},
        )

    logger.info(
        "Starting text extraction for book %s (publisher: %s, name: %s)",
        book_id,
        publisher_id,
        book_name,
    )

    import asyncio

    # Progress tracking for async update after extraction
    last_progress = {"current": 0, "total": 0}

    def on_progress(current: int, total: int) -> None:
        """Sync callback to track progress."""
        last_progress["current"] = current
        last_progress["total"] = total

    # Get extraction service and storage
    extraction_service = get_extraction_service()
    ai_storage = get_ai_storage()

    # Clean up any existing text files before re-extraction
    ai_storage.cleanup_text_directory(publisher_id, book_id, book_name)

    # Extract text from PDF
    result = await extraction_service.extract_book_pdf(
        book_id=book_id,
        publisher_id=publisher_id,
        book_name=book_name,
        progress_callback=on_progress,
    )

    # Report final progress
    await progress.report_progress("text_extraction", 100)

    # Save extracted text to storage
    saved = ai_storage.save_all(result)

    logger.info(
        "Text extraction completed: %d pages, %d words, method=%s",
        result.total_pages,
        result.total_word_count,
        result.method.value,
    )

    return {
        "total_pages": result.total_pages,
        "total_word_count": result.total_word_count,
        "method": result.method.value,
        "scanned_pages": result.scanned_page_count,
        "native_pages": result.native_page_count,
        "saved_files": len(saved.get("text_files", [])),
        "metadata_path": saved.get("metadata"),
    }


async def _run_segmentation(
    job_id: str,
    book_id: str,
    publisher_id: str,
    book_name: str,
    progress: ProgressReporter,
    text_extraction_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run segmentation stage.

    Segments the extracted text into logical modules/chapters.

    Args:
        job_id: Job ID
        book_id: Book ID
        publisher_id: Publisher ID
        book_name: Book folder name
        progress: Progress reporter
        text_extraction_result: Result from text extraction stage

    Returns:
        Segmentation result data

    Raises:
        QueueError: If book_name is missing or segmentation fails
    """
    if not book_name:
        raise QueueError(
            "book_name is required for segmentation",
            {"job_id": job_id, "book_id": book_id},
        )

    logger.info(
        "Starting segmentation for book %s (publisher: %s, name: %s)",
        book_id,
        publisher_id,
        book_name,
    )

    # Progress tracking
    def on_progress(current: int, total: int) -> None:
        """Sync callback to track progress."""
        pass  # Progress is reported via ProgressReporter

    # Get segmentation service and storage
    segmentation_service = get_segmentation_service()
    module_storage = get_module_storage()

    # Clean up any existing module files before re-segmentation
    module_storage.cleanup_modules_directory(publisher_id, book_id, book_name)

    # Run segmentation
    result = await segmentation_service.segment_book(
        book_id=book_id,
        publisher_id=publisher_id,
        book_name=book_name,
        progress_callback=on_progress,
    )

    # Report progress at 80%
    await progress.report_progress("segmentation", 80)

    # Save modules to storage
    saved = module_storage.save_all(result)

    # Report final progress
    await progress.report_progress("segmentation", 100)

    logger.info(
        "Segmentation completed: %d modules, method=%s",
        result.module_count,
        result.method.value,
    )

    return {
        "module_count": result.module_count,
        "total_word_count": result.total_word_count,
        "method": result.method.value,
        "saved_modules": len(saved.get("modules", [])),
        "metadata_path": saved.get("metadata"),
        "modules": [
            {"id": m.module_id, "title": m.title, "pages": len(m.pages)}
            for m in result.modules
        ],
    }


async def on_job_start(ctx: dict[str, Any]) -> None:
    """Called when a job starts.

    Args:
        ctx: arq context
    """
    logger.info("Worker starting job")


async def on_job_end(ctx: dict[str, Any]) -> None:
    """Called when a job ends.

    Args:
        ctx: arq context
    """
    logger.info("Worker finished job")
