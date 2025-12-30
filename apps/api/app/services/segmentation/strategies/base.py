"""Base class for segmentation strategies."""

from abc import ABC, abstractmethod

from app.services.segmentation.models import ModuleBoundary, SegmentationMethod


class SegmentationStrategy(ABC):
    """Abstract base class for segmentation strategies."""

    @property
    @abstractmethod
    def method(self) -> SegmentationMethod:
        """Return the segmentation method type."""
        pass

    @abstractmethod
    def detect_boundaries(
        self,
        pages: dict[int, str],
        **kwargs,
    ) -> list[ModuleBoundary]:
        """
        Detect module boundaries in the given pages.

        Args:
            pages: Dictionary mapping page numbers (1-indexed) to text content.
            **kwargs: Strategy-specific parameters.

        Returns:
            List of detected module boundaries, sorted by start_page.
        """
        pass

    def can_segment(self, pages: dict[int, str], **kwargs) -> bool:
        """
        Check if this strategy can segment the given content.

        Args:
            pages: Dictionary mapping page numbers to text content.
            **kwargs: Strategy-specific parameters.

        Returns:
            True if this strategy can produce meaningful segmentation.
        """
        boundaries = self.detect_boundaries(pages, **kwargs)
        return len(boundaries) > 0
