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

logger = logging.getLogger(__name__)


async def process_book_task(
    ctx: dict[str, Any],
    job_id: str,
    book_id: str,
    publisher_id: str,
    job_type: str,
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

    try:
        for stage in stages_to_run:
            try:
                await _run_processing_stage(
                    stage=stage,
                    job_id=job_id,
                    book_id=book_id,
                    publisher_id=publisher_id,
                    progress=progress,
                )
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
) -> None:
    """Run a single processing stage.

    This is a placeholder that will be implemented in future stories
    when the actual processing logic is built.

    Args:
        stage: Stage name
        job_id: Job ID
        book_id: Book ID
        publisher_id: Publisher ID
        progress: Progress reporter
    """
    logger.info("Running stage %s for job %s", stage, job_id)

    # Report initial progress for stage
    await progress.report_progress(stage, 0)

    # Placeholder - actual implementation in future stories
    # Each stage will call the appropriate service:
    # - text_extraction: PDF service
    # - segmentation: Text processing service
    # - topic_analysis: LLM service
    # - vocabulary: LLM service
    # - audio_generation: TTS service

    # For now, just mark progress
    await progress.report_progress(stage, 50)

    # Simulate completion
    await progress.report_progress(stage, 100)

    logger.info("Completed stage %s for job %s", stage, job_id)


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
