"""Native PDF text extraction using PyMuPDF."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import TYPE_CHECKING

import fitz  # pymupdf

from app.services.pdf.models import (
    ExtractionMethod,
    PageText,
    PDFCorruptedError,
    PDFPasswordProtectedError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text from PDF documents using PyMuPDF."""

    def __init__(self, pdf_data: bytes, book_id: str) -> None:
        """
        Initialize the PDF extractor.

        Args:
            pdf_data: Raw PDF file bytes.
            book_id: Book identifier for error reporting.
        """
        self.pdf_data = pdf_data
        self.book_id = book_id
        self._doc: fitz.Document | None = None

    def open(self) -> None:
        """
        Open the PDF document.

        Raises:
            PDFPasswordProtectedError: If PDF requires a password.
            PDFCorruptedError: If PDF is corrupted or invalid.
        """
        try:
            self._doc = fitz.open(stream=self.pdf_data, filetype="pdf")
        except fitz.FileDataError as e:
            raise PDFCorruptedError(self.book_id, str(e)) from e
        except Exception as e:
            raise PDFCorruptedError(self.book_id, f"Failed to open PDF: {e}") from e

        if self._doc.is_encrypted:
            if not self._doc.authenticate(""):
                self._doc.close()
                self._doc = None
                raise PDFPasswordProtectedError(self.book_id)

    def close(self) -> None:
        """Close the PDF document."""
        if self._doc:
            self._doc.close()
            self._doc = None

    def __enter__(self) -> PDFExtractor:
        self.open()
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object) -> None:
        self.close()

    @property
    def page_count(self) -> int:
        """Return the number of pages in the PDF."""
        if not self._doc:
            raise RuntimeError("PDF document not opened. Call open() first.")
        return len(self._doc)

    def extract_text_from_page(self, page_number: int) -> str:
        """
        Extract text from a single page with multi-column handling.

        Args:
            page_number: Zero-indexed page number.

        Returns:
            Extracted text from the page.

        Raises:
            RuntimeError: If document is not opened.
            IndexError: If page number is out of range.
        """
        if not self._doc:
            raise RuntimeError("PDF document not opened. Call open() first.")

        if page_number < 0 or page_number >= len(self._doc):
            raise IndexError(f"Page {page_number} out of range (0-{len(self._doc) - 1})")

        page = self._doc[page_number]
        return self._extract_text_with_layout(page)

    def _extract_text_with_layout(self, page: fitz.Page) -> str:
        """
        Extract text preserving reading order for multi-column layouts.

        Uses text block positions to sort content top-to-bottom, left-to-right.

        Args:
            page: PyMuPDF page object.

        Returns:
            Extracted text in proper reading order.
        """
        try:
            # Get text blocks with position info
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        except Exception as e:
            logger.warning(
                "Failed to extract text blocks for page %d: %s, falling back to simple extraction",
                page.number,
                e,
            )
            return page.get_text("text")

        # Filter to text blocks only (type 0 = text, type 1 = image)
        text_blocks = [b for b in blocks if b.get("type") == 0]

        if not text_blocks:
            return ""

        # Sort blocks by vertical position (y0), then horizontal (x0)
        # This handles multi-column layouts by reading top-to-bottom, left-to-right
        sorted_blocks = sorted(
            text_blocks,
            key=lambda b: (round(b["bbox"][1] / 20) * 20, b["bbox"][0]),  # Group by ~20px rows
        )

        text_parts: list[str] = []

        for block in sorted_blocks:
            block_lines: list[str] = []

            for line in block.get("lines", []):
                spans_text = []
                for span in line.get("spans", []):
                    span_text = span.get("text", "")
                    if span_text:
                        spans_text.append(span_text)

                line_text = "".join(spans_text).strip()
                if line_text:
                    block_lines.append(line_text)

            if block_lines:
                text_parts.append("\n".join(block_lines))

        return "\n\n".join(text_parts)

    def extract_all_pages(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[PageText]:
        """
        Extract text from all pages.

        Args:
            progress_callback: Optional callback(current_page, total_pages).

        Returns:
            List of PageText objects for each page.

        Raises:
            RuntimeError: If document is not opened.
        """
        if not self._doc:
            raise RuntimeError("PDF document not opened. Call open() first.")

        total_pages = len(self._doc)
        pages: list[PageText] = []

        for page_num in range(total_pages):
            text = self.extract_text_from_page(page_num)

            page_text = PageText(
                page_number=page_num + 1,  # 1-indexed for storage
                text=text,
                method=ExtractionMethod.NATIVE,
            )
            pages.append(page_text)

            if progress_callback:
                progress_callback(page_num + 1, total_pages)

        return pages

    def page_to_image(self, page_number: int, dpi: int = 150) -> bytes:
        """
        Convert a PDF page to PNG image bytes.

        Used for OCR fallback when page has no selectable text.

        Args:
            page_number: Zero-indexed page number.
            dpi: Resolution for the rendered image.

        Returns:
            PNG image as bytes.

        Raises:
            RuntimeError: If document is not opened.
            IndexError: If page number is out of range.
        """
        if not self._doc:
            raise RuntimeError("PDF document not opened. Call open() first.")

        if page_number < 0 or page_number >= len(self._doc):
            raise IndexError(f"Page {page_number} out of range (0-{len(self._doc) - 1})")

        page = self._doc[page_number]

        # Calculate zoom factor from DPI (72 is default PDF DPI)
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        # Render page to pixmap
        pix = page.get_pixmap(matrix=matrix)

        # Convert to PNG bytes
        return pix.tobytes("png")
