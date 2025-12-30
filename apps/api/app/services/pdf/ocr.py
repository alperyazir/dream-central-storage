"""OCR service using Gemini Vision for scanned PDF pages."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from app.services.llm import LLMProviderError, get_llm_service
from app.services.pdf.models import ExtractionMethod, OCRError, PageText

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.services.pdf.extractor import PDFExtractor

logger = logging.getLogger(__name__)

# OCR prompt template for extracting text from book page images
OCR_PROMPT = """Extract all text from this book page image.

Instructions:
- Extract ALL visible text including headers, body text, captions, and footnotes
- Preserve paragraph structure with blank lines between paragraphs
- Maintain reading order (left-to-right, top-to-bottom)
- Do NOT describe the image or add commentary
- If text is unclear, make best effort to transcribe
- Preserve any special formatting like bullet points or numbered lists

Return ONLY the extracted text, nothing else."""


class PDFOCRService:
    """OCR service for extracting text from scanned PDF pages using Gemini Vision."""

    def __init__(
        self,
        book_id: str,
        dpi: int = 150,
        batch_size: int = 5,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> None:
        """
        Initialize OCR service.

        Args:
            book_id: Book identifier for error reporting.
            dpi: Resolution for page image rendering.
            batch_size: Number of pages to process concurrently.
            max_retries: Maximum retry attempts per page.
            retry_delay: Base delay between retries (exponential backoff).
        """
        self.book_id = book_id
        self.dpi = dpi
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def ocr_page(
        self,
        page_image: bytes,
        page_number: int,
    ) -> str:
        """
        Extract text from a single page image using Gemini Vision.

        Args:
            page_image: PNG image bytes of the page.
            page_number: Page number for error reporting (1-indexed).

        Returns:
            Extracted text from the page.

        Raises:
            OCRError: If OCR fails after all retries.
        """
        llm_service = get_llm_service()
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await llm_service.complete_with_vision(
                    prompt=OCR_PROMPT,
                    images=[page_image],
                    use_fallback=False,  # Vision requires Gemini specifically
                    max_tokens=4096,
                    temperature=0.1,  # Low temperature for accurate extraction
                )
                return response.content.strip()

            except (LLMProviderError, ValueError) as e:
                last_error = e
                logger.warning(
                    "OCR attempt %d/%d failed for page %d: %s",
                    attempt + 1,
                    self.max_retries,
                    page_number,
                    str(e),
                )

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = self.retry_delay * (2**attempt)
                    await asyncio.sleep(wait_time)

        raise OCRError(
            book_id=self.book_id,
            page=page_number,
            reason=str(last_error) if last_error else "Unknown error",
        )

    async def ocr_pages(
        self,
        extractor: PDFExtractor,
        page_numbers: list[int],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[PageText]:
        """
        OCR multiple pages with batched concurrent processing.

        Args:
            extractor: Opened PDFExtractor instance for page image rendering.
            page_numbers: List of page numbers to OCR (0-indexed).
            progress_callback: Optional callback(current, total) for progress reporting.

        Returns:
            List of PageText objects with OCR-extracted text.
        """
        total_pages = len(page_numbers)
        results: dict[int, PageText] = {}
        completed = 0

        # Process in batches
        for batch_start in range(0, total_pages, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_pages)
            batch_pages = page_numbers[batch_start:batch_end]

            # Create tasks for batch
            tasks = []
            for page_num in batch_pages:
                tasks.append(self._ocr_single_page(extractor, page_num))

            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for page_num, result in zip(batch_pages, batch_results, strict=False):
                if isinstance(result, Exception):
                    logger.error(
                        "OCR failed for page %d: %s",
                        page_num + 1,
                        str(result),
                    )
                    # Store empty text for failed pages
                    results[page_num] = PageText(
                        page_number=page_num + 1,
                        text="",
                        method=ExtractionMethod.OCR,
                    )
                else:
                    results[page_num] = result

                completed += 1
                if progress_callback:
                    progress_callback(completed, total_pages)

        # Return in order
        return [results[pn] for pn in page_numbers]

    async def _ocr_single_page(
        self,
        extractor: PDFExtractor,
        page_number: int,
    ) -> PageText:
        """
        OCR a single page.

        Args:
            extractor: Opened PDFExtractor instance.
            page_number: Zero-indexed page number.

        Returns:
            PageText with OCR-extracted text.
        """
        # Convert page to image
        page_image = extractor.page_to_image(page_number, dpi=self.dpi)

        # OCR the image
        text = await self.ocr_page(page_image, page_number + 1)

        return PageText(
            page_number=page_number + 1,  # 1-indexed for storage
            text=text,
            method=ExtractionMethod.OCR,
        )

    async def ocr_page_from_extractor(
        self,
        extractor: PDFExtractor,
        page_number: int,
    ) -> PageText:
        """
        OCR a single page from an extractor instance.

        Convenience method for single-page OCR.

        Args:
            extractor: Opened PDFExtractor instance.
            page_number: Zero-indexed page number.

        Returns:
            PageText with OCR-extracted text.
        """
        return await self._ocr_single_page(extractor, page_number)
