"""Module segmentation service for AI book processing pipeline."""

from app.services.segmentation.models import (
    InvalidModuleDefinitionError,
    ManualModuleDefinition,
    Module,
    ModuleBoundary,
    NoTextFoundError,
    SegmentationError,
    SegmentationLimitError,
    SegmentationMethod,
    SegmentationResult,
)
from app.services.segmentation.service import (
    SegmentationService,
    get_segmentation_service,
)
from app.services.segmentation.storage import ModuleStorage, get_module_storage
from app.services.segmentation.strategies.base import SegmentationStrategy

__all__ = [
    # Service
    "SegmentationService",
    "get_segmentation_service",
    # Storage
    "ModuleStorage",
    "get_module_storage",
    # Data models
    "Module",
    "ModuleBoundary",
    "SegmentationResult",
    "SegmentationMethod",
    "ManualModuleDefinition",
    # Exceptions
    "SegmentationError",
    "NoTextFoundError",
    "InvalidModuleDefinitionError",
    "SegmentationLimitError",
    # Strategy base
    "SegmentationStrategy",
]
