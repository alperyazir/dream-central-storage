"""Fallback segmentation strategies for books with no clear structure."""

from __future__ import annotations

from app.services.segmentation.models import ModuleBoundary, SegmentationMethod
from app.services.segmentation.strategies.base import SegmentationStrategy


class SingleModuleStrategy(SegmentationStrategy):
    """
    Treat entire book as a single module.

    Used when no structure can be detected and the book
    should be processed as one unit.
    """

    def __init__(self, default_title: str = "Complete Book") -> None:
        """
        Initialize single module strategy.

        Args:
            default_title: Title for the single module.
        """
        self.default_title = default_title

    @property
    def method(self) -> SegmentationMethod:
        return SegmentationMethod.SINGLE_MODULE

    def detect_boundaries(
        self,
        pages: dict[int, str],
        **kwargs,
    ) -> list[ModuleBoundary]:
        """
        Create a single boundary for the entire book.

        Args:
            pages: Dictionary mapping page numbers to text content.
            **kwargs: Additional parameters.

        Returns:
            Single boundary starting at page 1.
        """
        if not pages:
            return []

        title = kwargs.get("title", self.default_title)

        return [ModuleBoundary(
            title=title,
            start_page=1,
            confidence=1.0,
        )]

    def can_segment(self, pages: dict[int, str], **kwargs) -> bool:
        """Always can segment (fallback)."""
        return len(pages) > 0


class PageSplitStrategy(SegmentationStrategy):
    """
    Split book by page count into equal-sized modules.

    Used when no structure detected but content is too large
    for a single module.
    """

    def __init__(
        self,
        pages_per_module: int = 20,
        min_pages_last_module: int = 5,
    ) -> None:
        """
        Initialize page split strategy.

        Args:
            pages_per_module: Target pages per module.
            min_pages_last_module: Minimum pages in last module
                (merge with previous if smaller).
        """
        self.pages_per_module = pages_per_module
        self.min_pages_last_module = min_pages_last_module

    @property
    def method(self) -> SegmentationMethod:
        return SegmentationMethod.PAGE_SPLIT

    def detect_boundaries(
        self,
        pages: dict[int, str],
        **kwargs,
    ) -> list[ModuleBoundary]:
        """
        Create boundaries at regular page intervals.

        Args:
            pages: Dictionary mapping page numbers to text content.
            **kwargs: Additional parameters.

        Returns:
            List of boundaries at page intervals.
        """
        if not pages:
            return []

        sorted_pages = sorted(pages.keys())
        total_pages = len(sorted_pages)
        pages_per_module = kwargs.get("pages_per_module", self.pages_per_module)

        if total_pages <= pages_per_module:
            # Book is small enough for single module
            return [ModuleBoundary(
                title="Module 1",
                start_page=sorted_pages[0],
                confidence=0.5,
            )]

        boundaries = []
        module_num = 1

        for i in range(0, total_pages, pages_per_module):
            start_idx = i
            start_page = sorted_pages[start_idx]

            # Check if remaining pages are too few
            remaining = total_pages - i
            if module_num > 1 and remaining < self.min_pages_last_module:
                # Don't create tiny last module - it was already included in previous
                break

            boundaries.append(ModuleBoundary(
                title=f"Module {module_num}",
                start_page=start_page,
                confidence=0.5,  # Low confidence for arbitrary splits
            ))
            module_num += 1

        return boundaries

    def can_segment(self, pages: dict[int, str], **kwargs) -> bool:
        """Can segment if there are pages."""
        return len(pages) > 0
