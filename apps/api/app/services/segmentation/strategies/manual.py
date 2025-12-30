"""Manual module definition strategy."""

from __future__ import annotations

from app.services.segmentation.models import (
    InvalidModuleDefinitionError,
    ManualModuleDefinition,
    ModuleBoundary,
    SegmentationMethod,
)
from app.services.segmentation.strategies.base import SegmentationStrategy


class ManualStrategy(SegmentationStrategy):
    """
    Use manually defined module definitions from admin or config.

    Allows explicit specification of module boundaries
    with validation to ensure complete coverage.
    """

    def __init__(
        self,
        definitions: list[ManualModuleDefinition] | None = None,
        require_full_coverage: bool = False,
    ) -> None:
        """
        Initialize manual strategy.

        Args:
            definitions: List of manual module definitions.
            require_full_coverage: If True, definitions must cover all pages.
        """
        self._definitions = definitions or []
        self.require_full_coverage = require_full_coverage

    @property
    def definitions(self) -> list[ManualModuleDefinition]:
        """Get current definitions."""
        return self._definitions

    @definitions.setter
    def definitions(self, value: list[ManualModuleDefinition]) -> None:
        """Set definitions."""
        self._definitions = value

    @property
    def method(self) -> SegmentationMethod:
        return SegmentationMethod.MANUAL

    def detect_boundaries(
        self,
        pages: dict[int, str],
        definitions: list[ManualModuleDefinition] | None = None,
        **kwargs,
    ) -> list[ModuleBoundary]:
        """
        Convert manual definitions to boundaries.

        Args:
            pages: Dictionary mapping page numbers to text content.
            definitions: Override definitions (optional).
            **kwargs: Additional parameters.

        Returns:
            List of module boundaries from definitions.

        Raises:
            InvalidModuleDefinitionError: If definitions are invalid.
        """
        defs = definitions or self._definitions
        if not defs:
            return []

        total_pages = max(pages.keys()) if pages else 0
        book_id = kwargs.get("book_id", "unknown")

        # Validate all definitions
        self._validate_definitions(defs, total_pages, book_id)

        # Convert to boundaries
        boundaries = []
        for defn in defs:
            boundaries.append(ModuleBoundary(
                title=defn.title,
                start_page=defn.start_page,
                confidence=1.0,  # Manual = full confidence
            ))

        # Sort by start page
        boundaries.sort(key=lambda b: b.start_page)
        return boundaries

    def _validate_definitions(
        self,
        definitions: list[ManualModuleDefinition],
        total_pages: int,
        book_id: str,
    ) -> None:
        """
        Validate manual definitions.

        Args:
            definitions: Definitions to validate.
            total_pages: Total pages in book.
            book_id: Book ID for error context.

        Raises:
            InvalidModuleDefinitionError: If validation fails.
        """
        if not definitions:
            raise InvalidModuleDefinitionError(
                book_id,
                "No module definitions provided"
            )

        all_errors = []

        # Validate each definition
        for i, defn in enumerate(definitions):
            errors = defn.validate(total_pages)
            for error in errors:
                all_errors.append(f"Module {i + 1}: {error}")

        # Check for overlaps
        sorted_defs = sorted(definitions, key=lambda d: d.start_page)
        for i in range(len(sorted_defs) - 1):
            current = sorted_defs[i]
            next_def = sorted_defs[i + 1]
            if current.end_page >= next_def.start_page:
                all_errors.append(
                    f"Overlap between '{current.title}' (ends {current.end_page}) "
                    f"and '{next_def.title}' (starts {next_def.start_page})"
                )

        # Check full coverage if required
        if self.require_full_coverage and total_pages > 0:
            covered = set()
            for defn in definitions:
                for page in range(defn.start_page, defn.end_page + 1):
                    covered.add(page)

            expected = set(range(1, total_pages + 1))
            missing = expected - covered
            if missing:
                all_errors.append(
                    f"Pages not covered: {sorted(missing)[:10]}..."
                    if len(missing) > 10
                    else f"Pages not covered: {sorted(missing)}"
                )

        if all_errors:
            raise InvalidModuleDefinitionError(
                book_id,
                "; ".join(all_errors)
            )

    def can_segment(self, pages: dict[int, str], **kwargs) -> bool:
        """Check if valid definitions are available."""
        definitions = kwargs.get("definitions") or self._definitions
        return len(definitions) > 0

    @classmethod
    def from_config(
        cls,
        config: list[dict],
        require_full_coverage: bool = False,
    ) -> ManualStrategy:
        """
        Create strategy from config dictionary.

        Args:
            config: List of dicts with title, start_page, end_page.
            require_full_coverage: If True, require full page coverage.

        Returns:
            ManualStrategy instance.
        """
        definitions = []
        for item in config:
            definitions.append(ManualModuleDefinition(
                title=item.get("title", "Untitled"),
                start_page=int(item.get("start_page", 1)),
                end_page=int(item.get("end_page", 1)),
            ))
        return cls(definitions=definitions, require_full_coverage=require_full_coverage)
