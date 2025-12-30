"""Scanned PDF detection logic."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.services.pdf.models import ExtractionMethod, PDFAnalysisResult

if TYPE_CHECKING:
    from app.services.pdf.extractor import PDFExtractor

logger = logging.getLogger(__name__)


class ScannedPDFDetector:
    """Detect whether PDF pages are scanned (image-based) or native (text-based)."""

    def __init__(
        self,
        min_char_threshold: int = 50,
        min_word_threshold: int = 10,
    ) -> None:
        """
        Initialize the detector.

        Args:
            min_char_threshold: Minimum characters for a page to be considered native.
            min_word_threshold: Minimum words for a page to be considered native.
        """
        self.min_char_threshold = min_char_threshold
        self.min_word_threshold = min_word_threshold

    def is_scanned_page(self, text: str) -> bool:
        """
        Determine if a page is scanned based on extracted text.

        A page is considered scanned if:
        - Character count < min_char_threshold, OR
        - Word count < min_word_threshold

        Args:
            text: Extracted text from the page.

        Returns:
            True if page appears to be scanned (image-based), False if native (text-based).
        """
        char_count = len(text.strip())
        word_count = len(text.split()) if text.strip() else 0

        is_scanned = char_count < self.min_char_threshold or word_count < self.min_word_threshold

        if is_scanned:
            logger.debug(
                "Page detected as scanned: %d chars, %d words (thresholds: %d chars, %d words)",
                char_count,
                word_count,
                self.min_char_threshold,
                self.min_word_threshold,
            )

        return is_scanned

    def analyze_pdf(self, extractor: PDFExtractor) -> PDFAnalysisResult:
        """
        Analyze an entire PDF to classify pages as scanned or native.

        Args:
            extractor: Opened PDFExtractor instance.

        Returns:
            PDFAnalysisResult with classification details.
        """
        total_pages = extractor.page_count
        scanned_pages = 0
        native_pages = 0
        scanned_page_numbers: list[int] = []

        for page_num in range(total_pages):
            text = extractor.extract_text_from_page(page_num)

            if self.is_scanned_page(text):
                scanned_pages += 1
                scanned_page_numbers.append(page_num + 1)  # 1-indexed
            else:
                native_pages += 1

        # Classify overall document
        if scanned_pages == 0:
            classification = ExtractionMethod.NATIVE
        elif native_pages == 0:
            classification = ExtractionMethod.OCR
        else:
            classification = ExtractionMethod.MIXED

        logger.info(
            "PDF analysis complete: %d total, %d native, %d scanned -> %s",
            total_pages,
            native_pages,
            scanned_pages,
            classification.value,
        )

        return PDFAnalysisResult(
            total_pages=total_pages,
            scanned_pages=scanned_pages,
            native_pages=native_pages,
            classification=classification,
            scanned_page_numbers=scanned_page_numbers,
        )

    def analyze_page_texts(self, texts: list[str]) -> PDFAnalysisResult:
        """
        Analyze pre-extracted page texts to classify pages.

        Useful when texts have already been extracted.

        Args:
            texts: List of extracted text strings, one per page.

        Returns:
            PDFAnalysisResult with classification details.
        """
        total_pages = len(texts)
        scanned_pages = 0
        native_pages = 0
        scanned_page_numbers: list[int] = []

        for idx, text in enumerate(texts):
            if self.is_scanned_page(text):
                scanned_pages += 1
                scanned_page_numbers.append(idx + 1)  # 1-indexed
            else:
                native_pages += 1

        # Classify overall document
        if scanned_pages == 0:
            classification = ExtractionMethod.NATIVE
        elif native_pages == 0:
            classification = ExtractionMethod.OCR
        else:
            classification = ExtractionMethod.MIXED

        return PDFAnalysisResult(
            total_pages=total_pages,
            scanned_pages=scanned_pages,
            native_pages=native_pages,
            classification=classification,
            scanned_page_numbers=scanned_page_numbers,
        )
