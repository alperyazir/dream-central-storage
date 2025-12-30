"""Vocabulary extraction service for AI book processing pipeline."""

from app.services.vocabulary_extraction.models import (
    BookVocabularyResult,
    DuplicateVocabularyError,
    InvalidLLMResponseError,
    LLMExtractionError,
    ModuleVocabularyResult,
    NoModulesFoundError,
    PartOfSpeech,
    VocabularyExtractionError,
    VocabularyWord,
)
from app.services.vocabulary_extraction.prompts import (
    SYSTEM_PROMPT,
    VOCABULARY_EXTRACTION_PROMPT,
    build_vocabulary_extraction_prompt,
)
from app.services.vocabulary_extraction.service import (
    VocabularyExtractionService,
    get_vocabulary_extraction_service,
)
from app.services.vocabulary_extraction.storage import (
    VocabularyStorage,
    get_vocabulary_storage,
)

__all__ = [
    # Service
    "VocabularyExtractionService",
    "get_vocabulary_extraction_service",
    # Storage
    "VocabularyStorage",
    "get_vocabulary_storage",
    # Data models
    "VocabularyWord",
    "ModuleVocabularyResult",
    "BookVocabularyResult",
    # Enums
    "PartOfSpeech",
    # Exceptions
    "VocabularyExtractionError",
    "LLMExtractionError",
    "NoModulesFoundError",
    "InvalidLLMResponseError",
    "DuplicateVocabularyError",
    # Prompts
    "SYSTEM_PROMPT",
    "VOCABULARY_EXTRACTION_PROMPT",
    "build_vocabulary_extraction_prompt",
]
