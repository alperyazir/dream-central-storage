"""AI-assisted segmentation strategy using LLM."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.services.segmentation.models import ModuleBoundary, SegmentationMethod
from app.services.segmentation.strategies.base import SegmentationStrategy

if TYPE_CHECKING:
    from app.services.llm import LLMService

logger = logging.getLogger(__name__)


SEGMENTATION_PROMPT = """Analyze this book text and identify logical module/chapter boundaries.

Instructions:
- Identify distinct units, chapters, or modules in the content
- Return the title and starting page number for each module
- Look for topic changes, section headers, or natural content divisions
- If no clear structure exists, suggest logical divisions by topic
- Return as a JSON array (no markdown, just raw JSON)

Text excerpt with page markers:
{text_excerpt}

Return ONLY a JSON array in this exact format (no other text):
[
  {{"title": "Module title here", "start_page": 1}},
  {{"title": "Next module title", "start_page": 15}}
]
"""


class AIAssistedStrategy(SegmentationStrategy):
    """
    Use LLM to identify logical segment boundaries.

    Sends book text to AI model for intelligent segmentation
    when header/TOC detection fails.
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        max_text_length: int = 8000,
        min_boundaries: int = 2,
    ) -> None:
        """
        Initialize AI-assisted strategy.

        Args:
            llm_service: LLM service instance. If None, will get from singleton.
            max_text_length: Maximum text length to send to LLM.
            min_boundaries: Minimum boundaries for valid segmentation.
        """
        self._llm_service = llm_service
        self.max_text_length = max_text_length
        self.min_boundaries = min_boundaries

    @property
    def llm_service(self) -> LLMService:
        """Get LLM service (lazy load)."""
        if self._llm_service is None:
            from app.services.llm import get_llm_service
            self._llm_service = get_llm_service()
        return self._llm_service

    @property
    def method(self) -> SegmentationMethod:
        return SegmentationMethod.AI_ASSISTED

    def detect_boundaries(
        self,
        pages: dict[int, str],
        **kwargs,
    ) -> list[ModuleBoundary]:
        """
        Detect boundaries using AI analysis.

        Note: This is a synchronous wrapper. For async usage,
        use detect_boundaries_async().

        Args:
            pages: Dictionary mapping page numbers to text content.
            **kwargs: Additional parameters.

        Returns:
            List of AI-detected module boundaries.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're already in an async context - can't use run
                # Return empty, caller should use async method
                logger.warning(
                    "AIAssistedStrategy.detect_boundaries called from async context. "
                    "Use detect_boundaries_async() instead."
                )
                return []
            return loop.run_until_complete(
                self.detect_boundaries_async(pages, **kwargs)
            )
        except RuntimeError:
            # No event loop
            return asyncio.run(self.detect_boundaries_async(pages, **kwargs))

    async def detect_boundaries_async(
        self,
        pages: dict[int, str],
        **kwargs,
    ) -> list[ModuleBoundary]:
        """
        Detect boundaries using AI analysis (async).

        Args:
            pages: Dictionary mapping page numbers to text content.
            **kwargs: Additional parameters.

        Returns:
            List of AI-detected module boundaries.
        """
        # Prepare text excerpt with page markers
        text_excerpt = self._prepare_text_excerpt(pages)
        if not text_excerpt:
            return []

        # Build prompt
        prompt = SEGMENTATION_PROMPT.format(text_excerpt=text_excerpt)

        try:
            # Call LLM
            response = await self.llm_service.simple_completion(
                prompt=prompt,
                system_prompt=(
                    "You are a document analysis assistant. "
                    "Return only valid JSON arrays, no markdown or explanations."
                ),
                temperature=0.3,  # Lower temperature for structured output
            )

            # Parse response
            boundaries = self._parse_response(response)
            return boundaries

        except Exception as e:
            logger.error(f"AI segmentation failed: {e}")
            return []

    def _prepare_text_excerpt(self, pages: dict[int, str]) -> str:
        """Prepare text excerpt with page markers for LLM."""
        parts = []
        total_length = 0

        for page_num in sorted(pages.keys()):
            text = pages.get(page_num, "").strip()
            if not text:
                continue

            # Add page marker
            page_marker = f"\n--- Page {page_num} ---\n"
            excerpt = text[:500]  # First 500 chars per page

            if total_length + len(page_marker) + len(excerpt) > self.max_text_length:
                break

            parts.append(page_marker + excerpt)
            total_length += len(page_marker) + len(excerpt)

        return "".join(parts)

    def _parse_response(self, response: str) -> list[ModuleBoundary]:
        """Parse LLM JSON response into boundaries."""
        boundaries = []

        # Clean response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            response = response.strip()

        try:
            data = json.loads(response)

            if not isinstance(data, list):
                logger.warning("LLM response is not a list")
                return []

            for item in data:
                if not isinstance(item, dict):
                    continue

                title = item.get("title", "")
                start_page = item.get("start_page")

                if not title or start_page is None:
                    continue

                try:
                    start_page = int(start_page)
                except (ValueError, TypeError):
                    continue

                if start_page < 1:
                    continue

                boundaries.append(ModuleBoundary(
                    title=str(title).strip(),
                    start_page=start_page,
                    confidence=0.7,  # AI has moderate confidence
                ))

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return []

        # Sort by page
        boundaries.sort(key=lambda b: b.start_page)
        return boundaries

    def can_segment(self, pages: dict[int, str], **kwargs) -> bool:
        """
        Check if AI can segment (always True if LLM available).

        Note: This doesn't actually call the LLM - it just checks availability.
        """
        try:
            # Check if LLM service is available
            return self.llm_service.primary_provider is not None
        except Exception:
            return False
