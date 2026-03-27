"""AI Processing Queue System.

This module provides a background job queue for AI book processing tasks
using arq with Redis for async, reliable job execution.
"""

from app.services.queue.models import (
    PROCESSING_STAGES,
    JobAlreadyExistsError,
    JobNotFoundError,
    JobPriority,
    ProcessingJob,
    ProcessingJobType,
    ProcessingStatus,
    QueueConnectionError,
    QueueError,
    QueueStats,
)
from app.services.queue.redis import (
    RedisConnection,
    close_redis_connection,
    get_redis_connection,
)
from app.services.queue.repository import JobRepository
from app.services.queue.service import (
    ProgressReporter,
    QueueService,
    close_queue_service,
    get_queue_service,
)

__all__ = [
    # Enums
    "JobPriority",
    "ProcessingJobType",
    "ProcessingStatus",
    # Data classes
    "ProcessingJob",
    "QueueStats",
    # Constants
    "PROCESSING_STAGES",
    # Exceptions
    "JobAlreadyExistsError",
    "JobNotFoundError",
    "QueueConnectionError",
    "QueueError",
    # Redis
    "RedisConnection",
    "get_redis_connection",
    "close_redis_connection",
    # Repository
    "JobRepository",
    # Service
    "QueueService",
    "ProgressReporter",
    "get_queue_service",
    "close_queue_service",
]
