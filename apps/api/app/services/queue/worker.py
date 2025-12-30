"""Worker runner configuration for arq."""

import asyncio
import logging
import signal
import sys
from typing import Any

from arq.connections import RedisSettings
from arq.worker import Worker

from app.core.config import get_settings
from app.services.queue.tasks import (
    process_book_task,
    on_job_start,
    on_job_end,
)

logger = logging.getLogger(__name__)

# Flag for graceful shutdown
_shutdown_requested = False


def _get_retry_delay(attempt: int) -> float:
    """Calculate retry delay with exponential backoff.

    Args:
        attempt: Current attempt number (0-indexed)

    Returns:
        Delay in seconds
    """
    settings = get_settings()
    base_delay = settings.queue_retry_delay_seconds
    # Exponential backoff: base * 2^attempt, capped at 1 hour
    return min(base_delay * (2 ** attempt), 3600)


class WorkerSettings:
    """arq worker configuration.

    This class defines the worker settings used by arq to configure
    the background worker process.
    """

    # Task functions to register
    functions = [process_book_task]

    # Lifecycle hooks
    on_startup = on_job_start
    on_shutdown = on_job_end

    # Redis connection settings (set dynamically)
    redis_settings: RedisSettings = None  # type: ignore

    # Concurrency and timeout settings (set dynamically)
    max_jobs: int = 3
    job_timeout: int = 3600
    max_tries: int = 3
    health_check_interval: int = 30

    # Retry configuration
    retry_jobs: bool = True

    @staticmethod
    def get_retry_delay(attempt: int) -> float:
        """Get retry delay for attempt."""
        return _get_retry_delay(attempt)

    # Queue name (set dynamically)
    queue_name: str = "arq:queue"

    @classmethod
    def configure(cls) -> type["WorkerSettings"]:
        """Configure settings from environment.

        Returns:
            Configured WorkerSettings class
        """
        settings = get_settings()

        cls.redis_settings = RedisSettings.from_dsn(settings.redis_url)
        cls.max_jobs = settings.queue_max_concurrency
        cls.job_timeout = settings.queue_job_timeout_seconds
        cls.max_tries = settings.queue_max_retries
        # Listen to normal priority queue by default
        cls.queue_name = f"{settings.queue_name}:normal"

        return cls


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup hook.

    Args:
        ctx: arq context
    """
    logger.info("Worker starting up")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown hook.

    Args:
        ctx: arq context
    """
    logger.info("Worker shutting down")


def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals for graceful termination.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("Shutdown signal received, finishing current jobs...")


async def run_worker() -> None:
    """Run the arq worker.

    This function starts the worker process and handles graceful shutdown.
    """
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Configure settings
    settings_cls = WorkerSettings.configure()

    logger.info(
        "Starting worker with max_jobs=%d, job_timeout=%d, max_tries=%d",
        settings_cls.max_jobs,
        settings_cls.job_timeout,
        settings_cls.max_tries,
    )

    # Create and run worker
    worker = Worker(
        functions=settings_cls.functions,
        redis_settings=settings_cls.redis_settings,
        max_jobs=settings_cls.max_jobs,
        job_timeout=settings_cls.job_timeout,
        max_tries=settings_cls.max_tries,
        health_check_interval=settings_cls.health_check_interval,
        retry_jobs=settings_cls.retry_jobs,
        queue_name=settings_cls.queue_name,
        on_startup=startup,
        on_shutdown=shutdown,
    )

    try:
        await worker.async_run()
    except asyncio.CancelledError:
        logger.info("Worker cancelled")
    finally:
        await worker.close()
        logger.info("Worker stopped")


def main() -> None:
    """Entry point for running the worker from command line.

    Usage:
        python -m app.services.queue.worker
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Initializing AI processing queue worker")

    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error("Worker failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
