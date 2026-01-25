"""Material extraction service package."""

from app.services.material_extraction.models import (
    ExtractionMethod,
    FileType,
    MaterialExtractionError,
    MaterialExtractionResult,
    PageText,
    UnsupportedFileTypeError,
    ExtractionFailedError,
)
from app.services.material_extraction.service import (
    MaterialExtractionService,
    get_material_extraction_service,
)

__all__ = [
    "ExtractionMethod",
    "FileType",
    "MaterialExtractionError",
    "MaterialExtractionResult",
    "PageText",
    "UnsupportedFileTypeError",
    "ExtractionFailedError",
    "MaterialExtractionService",
    "get_material_extraction_service",
]
