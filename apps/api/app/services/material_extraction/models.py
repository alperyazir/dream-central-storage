"""Models for material text extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ExtractionMethod(str, Enum):
    """Text extraction method used."""
    NATIVE = "native"
    OCR = "ocr"
    MIXED = "mixed"
    DIRECT = "direct"  # For TXT files


class FileType(str, Enum):
    """Supported file types for extraction."""
    PDF = "pdf"
    TXT = "txt"
    DOC = "doc"
    DOCX = "docx"

    @classmethod
    def from_extension(cls, extension: str) -> FileType | None:
        """Get FileType from file extension."""
        ext = extension.lower().lstrip(".")
        try:
            return cls(ext)
        except ValueError:
            return None

    @property
    def is_text_extractable(self) -> bool:
        """Check if this file type supports text extraction."""
        return self in {FileType.PDF, FileType.TXT, FileType.DOCX}


@dataclass
class PageText:
    """Extracted text from a single page."""
    page_number: int
    text: str
    method: ExtractionMethod = ExtractionMethod.NATIVE
    word_count: int = 0

    def __post_init__(self) -> None:
        if self.word_count == 0 and self.text:
            self.word_count = len(self.text.split())


@dataclass
class MaterialExtractionResult:
    """Result of material text extraction."""
    material_id: int
    teacher_id: str
    material_name: str
    file_type: FileType
    total_pages: int
    total_word_count: int
    method: ExtractionMethod
    pages: list[PageText] = field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if extraction was successful."""
        return self.error is None and self.total_pages > 0


class MaterialExtractionError(Exception):
    """Base exception for material extraction errors."""
    def __init__(self, message: str, material_name: str = "") -> None:
        self.message = message
        self.material_name = material_name
        super().__init__(f"[{material_name}] {message}" if material_name else message)


class UnsupportedFileTypeError(MaterialExtractionError):
    """Raised when file type is not supported for extraction."""
    pass


class FileNotFoundError(MaterialExtractionError):
    """Raised when material file is not found in storage."""
    pass


class ExtractionFailedError(MaterialExtractionError):
    """Raised when text extraction fails."""
    pass
