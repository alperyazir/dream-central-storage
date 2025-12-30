"""AI processing automation services."""

from app.services.ai_processing.auto_trigger import (
    AutoProcessingService,
    get_auto_processing_service,
    trigger_auto_processing,
)

__all__ = [
    "AutoProcessingService",
    "get_auto_processing_service",
    "trigger_auto_processing",
]
