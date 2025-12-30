"""Table of Contents (TOC) based segmentation strategy."""

from __future__ import annotations

import re
from typing import Pattern

from app.services.segmentation.models import ModuleBoundary, SegmentationMethod
from app.services.segmentation.strategies.base import SegmentationStrategy


class TOCBasedStrategy(SegmentationStrategy):
    """
    Detect module boundaries from Table of Contents.

    Parses TOC entries to extract chapter/module titles and page numbers.
    Handles various TOC formats:
    - "Chapter 1 ........ 5"
    - "Unit 1: Greetings    15"
    - "Introduction _______ 3"
    """

    # Patterns to detect TOC page header
    TOC_HEADER_PATTERNS = [
        re.compile(r'table\s+of\s+contents', re.IGNORECASE),
        re.compile(r'^contents$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'^index$', re.IGNORECASE | re.MULTILINE),
        re.compile(r'icerik\s*tablosu', re.IGNORECASE),  # Turkish
        re.compile(r'^icerik$', re.IGNORECASE | re.MULTILINE),  # Turkish
    ]

    # Pattern to match TOC entries with page numbers
    TOC_ENTRY_PATTERNS: list[Pattern] = [
        # "Chapter 1: Title ........ 15"
        re.compile(
            r'^(.+?)\s*[\.\-_·•]{3,}\s*(\d+)\s*$',
            re.MULTILINE
        ),
        # "Chapter 1: Title          15" (spaces only)
        re.compile(
            r'^(.{10,60}?)\s{5,}(\d+)\s*$',
            re.MULTILINE
        ),
        # "15    Chapter 1: Title" (page number first)
        re.compile(
            r'^\s*(\d+)\s{3,}(.{10,60})$',
            re.MULTILINE
        ),
    ]

    def __init__(
        self,
        max_toc_pages: int = 10,
        min_entries: int = 2,
    ) -> None:
        """
        Initialize TOC-based strategy.

        Args:
            max_toc_pages: Maximum pages to search for TOC (from start).
            min_entries: Minimum TOC entries required for valid segmentation.
        """
        self.max_toc_pages = max_toc_pages
        self.min_entries = min_entries

    @property
    def method(self) -> SegmentationMethod:
        return SegmentationMethod.TOC_BASED

    def detect_boundaries(
        self,
        pages: dict[int, str],
        **kwargs,
    ) -> list[ModuleBoundary]:
        """
        Detect module boundaries from TOC.

        Args:
            pages: Dictionary mapping page numbers to text content.
            **kwargs: Additional parameters.

        Returns:
            List of module boundaries from TOC.
        """
        # Find TOC page(s)
        toc_text = self._find_toc_text(pages)
        if not toc_text:
            return []

        # Parse TOC entries
        entries = self._parse_toc_entries(toc_text)

        # Convert to boundaries
        boundaries = []
        for title, page_num in entries:
            # Clean up the title
            clean_title = self._clean_title(title)
            if clean_title and len(clean_title) >= 3:
                boundaries.append(ModuleBoundary(
                    title=clean_title,
                    start_page=page_num,
                    confidence=0.9,  # High confidence for TOC entries
                ))

        # Sort by page number and deduplicate
        boundaries.sort(key=lambda b: b.start_page)
        return self._deduplicate(boundaries)

    def _find_toc_text(self, pages: dict[int, str]) -> str:
        """Find and extract TOC text from first pages."""
        toc_pages: list[str] = []
        found_toc = False

        for page_num in sorted(pages.keys())[:self.max_toc_pages]:
            text = pages.get(page_num, "")
            if not text:
                continue

            # Check if this page contains TOC header
            if self._is_toc_page(text):
                found_toc = True
                toc_pages.append(text)
            elif found_toc:
                # Continue collecting if TOC seems to span multiple pages
                if self._looks_like_toc_continuation(text):
                    toc_pages.append(text)
                else:
                    break

        return "\n".join(toc_pages)

    def _is_toc_page(self, text: str) -> bool:
        """Check if page contains TOC header."""
        for pattern in self.TOC_HEADER_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def _looks_like_toc_continuation(self, text: str) -> bool:
        """Check if page looks like TOC continuation."""
        # If it has multiple entries with page numbers, likely TOC
        entry_count = 0
        for pattern in self.TOC_ENTRY_PATTERNS:
            matches = pattern.findall(text)
            entry_count += len(matches)
        return entry_count >= 3

    def _parse_toc_entries(self, text: str) -> list[tuple[str, int]]:
        """Parse TOC text and extract entries."""
        entries: list[tuple[str, int]] = []
        seen_pages: set[int] = set()

        for pattern in self.TOC_ENTRY_PATTERNS:
            for match in pattern.finditer(text):
                groups = match.groups()

                # Determine which group is title and which is page
                if groups[0].isdigit():
                    page_num = int(groups[0])
                    title = groups[1]
                else:
                    title = groups[0]
                    page_num = int(groups[1])

                # Skip duplicates and invalid entries
                if page_num in seen_pages:
                    continue
                if page_num < 1 or page_num > 1000:
                    continue

                entries.append((title.strip(), page_num))
                seen_pages.add(page_num)

        # Sort by page number
        entries.sort(key=lambda x: x[1])
        return entries

    def _clean_title(self, title: str) -> str:
        """Clean up TOC entry title."""
        # Remove leading/trailing dots, dashes, spaces
        title = re.sub(r'^[\.\-_·•\s]+', '', title)
        title = re.sub(r'[\.\-_·•\s]+$', '', title)

        # Remove excessive whitespace
        title = re.sub(r'\s+', ' ', title)

        return title.strip()

    def _deduplicate(self, boundaries: list[ModuleBoundary]) -> list[ModuleBoundary]:
        """Remove duplicate entries (same page or very similar titles)."""
        result: list[ModuleBoundary] = []
        seen_pages: set[int] = set()

        for boundary in boundaries:
            if boundary.start_page not in seen_pages:
                result.append(boundary)
                seen_pages.add(boundary.start_page)

        return result

    def can_segment(self, pages: dict[int, str], **kwargs) -> bool:
        """Check if valid TOC can be found."""
        boundaries = self.detect_boundaries(pages, **kwargs)
        return len(boundaries) >= self.min_entries
