"""PDF extraction service for AI book processing pipeline."""

from app.services.pdf.detector import ScannedPDFDetector
from app.services.pdf.extractor import PDFExtractor
from app.services.pdf.models import (
    ExtractionMethod,
    OCRError,
    PageText,
    PDFAnalysisResult,
    PDFCorruptedError,
    PDFExtractionError,
    PDFExtractionResult,
    PDFNotFoundError,
    PDFPageLimitExceededError,
    PDFPasswordProtectedError,
)
from app.services.pdf.ocr import PDFOCRService
from app.services.pdf.service import PDFExtractionService, get_extraction_service
from app.services.pdf.storage import AIDataStorage, get_ai_storage

__all__ = [
    # Service
    "PDFExtractionService",
    "get_extraction_service",
    # Storage
    "AIDataStorage",
    "get_ai_storage",
    # Extractor, Detector & OCR
    "PDFExtractor",
    "ScannedPDFDetector",
    "PDFOCRService",
    # Data models
    "ExtractionMethod",
    "PageText",
    "PDFAnalysisResult",
    "PDFExtractionResult",
    # Exceptions
    "PDFExtractionError",
    "PDFNotFoundError",
    "PDFPasswordProtectedError",
    "PDFCorruptedError",
    "PDFPageLimitExceededError",
    "OCRError",
]
