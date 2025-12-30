"""Header-based segmentation strategy."""

from __future__ import annotations

import re
from typing import Pattern

from app.services.segmentation.models import ModuleBoundary, SegmentationMethod
from app.services.segmentation.strategies.base import SegmentationStrategy


# Number word mappings for detection
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
    # Turkish numbers
    "bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5,
    "alti": 6, "yedi": 7, "sekiz": 8, "dokuz": 9, "on": 10,
}

# Roman numeral patterns
ROMAN_NUMERAL_PATTERN = re.compile(
    r'^(M{0,3})(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$',
    re.IGNORECASE
)

ROMAN_VALUES = {
    'I': 1, 'V': 5, 'X': 10, 'L': 50,
    'C': 100, 'D': 500, 'M': 1000
}


def roman_to_int(roman: str) -> int | None:
    """Convert roman numeral to integer."""
    if not roman or not ROMAN_NUMERAL_PATTERN.match(roman):
        return None

    result = 0
    prev_value = 0
    for char in reversed(roman.upper()):
        value = ROMAN_VALUES.get(char, 0)
        if value < prev_value:
            result -= value
        else:
            result += value
        prev_value = value
    return result if result > 0 else None


class HeaderBasedStrategy(SegmentationStrategy):
    """
    Detect module boundaries from headers and titles in text.

    Supports patterns like:
    - "Unit 1", "Chapter 2", "Module 3"
    - "Unit One", "Chapter Two"
    - "I. Introduction", "II. Methods"
    - "1. Getting Started"
    - Turkish: "Unite 1", "Bolum 2", "Konu 3"
    """

    # Header keyword patterns (English and Turkish)
    HEADER_KEYWORDS = [
        # English
        "unit", "chapter", "module", "section", "part", "lesson",
        # Turkish
        "unite", "bolum", "konu", "ders", "kisim",
    ]

    def __init__(self, min_confidence: float = 0.5) -> None:
        """
        Initialize header-based strategy.

        Args:
            min_confidence: Minimum confidence threshold for boundaries.
        """
        self.min_confidence = min_confidence
        self._patterns = self._build_patterns()

    @property
    def method(self) -> SegmentationMethod:
        return SegmentationMethod.HEADER_BASED

    def _build_patterns(self) -> list[tuple[Pattern, float]]:
        """Build regex patterns for header detection with confidence scores."""
        patterns = []

        # Pattern 1: "Unit 1:", "Chapter 2 -", etc. (highest confidence)
        keywords = "|".join(self.HEADER_KEYWORDS)
        patterns.append((
            re.compile(
                rf'^({keywords})\s*(\d+)\s*[:\-–—]?\s*(.*)$',
                re.IGNORECASE | re.MULTILINE
            ),
            1.0
        ))

        # Pattern 2: "Unit One", "Chapter Two" (with word numbers)
        number_words = "|".join(NUMBER_WORDS.keys())
        patterns.append((
            re.compile(
                rf'^({keywords})\s+({number_words})\s*[:\-–—]?\s*(.*)$',
                re.IGNORECASE | re.MULTILINE
            ),
            0.95
        ))

        # Pattern 3: Roman numerals "I.", "II.", "III."
        patterns.append((
            re.compile(
                r'^([IVXLCDM]+)\.\s+(.+)$',
                re.IGNORECASE | re.MULTILINE
            ),
            0.8
        ))

        # Pattern 4: Simple numbered "1.", "2.", "3." at line start
        patterns.append((
            re.compile(
                r'^(\d+)\.\s+([A-Z][a-zA-Z\s]{3,50})$',
                re.MULTILINE
            ),
            0.6
        ))

        return patterns

    def detect_boundaries(
        self,
        pages: dict[int, str],
        **kwargs,
    ) -> list[ModuleBoundary]:
        """
        Detect module boundaries from headers in page text.

        Args:
            pages: Dictionary mapping page numbers to text content.
            **kwargs: Additional parameters (unused).

        Returns:
            List of detected module boundaries.
        """
        boundaries: list[ModuleBoundary] = []
        seen_titles: set[str] = set()

        for page_num in sorted(pages.keys()):
            text = pages[page_num]
            if not text or not text.strip():
                continue

            page_boundaries = self._detect_in_page(text, page_num)

            for boundary in page_boundaries:
                # Skip duplicates
                normalized_title = boundary.title.lower().strip()
                if normalized_title in seen_titles:
                    continue

                # Apply confidence filter
                if boundary.confidence >= self.min_confidence:
                    boundaries.append(boundary)
                    seen_titles.add(normalized_title)

        # Sort by page number
        boundaries.sort(key=lambda b: b.start_page)
        return boundaries

    def _detect_in_page(self, text: str, page_num: int) -> list[ModuleBoundary]:
        """Detect boundaries in a single page."""
        boundaries = []
        lines = text.split('\n')

        for line in lines[:30]:  # Focus on top portion of page
            line = line.strip()
            if not line or len(line) < 3:
                continue

            boundary = self._match_line(line, page_num)
            if boundary:
                boundaries.append(boundary)

        return boundaries

    def _match_line(self, line: str, page_num: int) -> ModuleBoundary | None:
        """Try to match a line against header patterns."""
        for pattern, confidence in self._patterns:
            match = pattern.match(line)
            if match:
                title = self._extract_title(match, line)
                if title and len(title) >= 3:
                    return ModuleBoundary(
                        title=title,
                        start_page=page_num,
                        confidence=confidence,
                    )
        return None

    def _extract_title(self, match: re.Match, original_line: str) -> str:
        """Extract a clean title from the match."""
        groups = match.groups()

        # For keyword + number patterns
        if len(groups) >= 2:
            keyword = groups[0]
            number_part = groups[1]
            title_part = groups[2] if len(groups) > 2 else ""

            # Check if number_part is a word number
            if number_part.lower() in NUMBER_WORDS:
                number = NUMBER_WORDS[number_part.lower()]
                number_part = str(number)

            # Check if it's a roman numeral (for pattern 3)
            if keyword.upper() in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
                                   'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX']:
                # Roman numeral pattern
                return f"{keyword}. {number_part}".strip()

            # Build title
            if title_part and title_part.strip():
                return f"{keyword.title()} {number_part}: {title_part.strip()}"
            else:
                return f"{keyword.title()} {number_part}"

        # For simpler patterns
        if len(groups) == 2:
            return f"{groups[0]}. {groups[1]}".strip()

        return original_line.strip()

    def can_segment(self, pages: dict[int, str], **kwargs) -> bool:
        """Check if meaningful headers can be detected."""
        boundaries = self.detect_boundaries(pages, **kwargs)
        # Need at least 2 boundaries for meaningful segmentation
        return len(boundaries) >= 2
