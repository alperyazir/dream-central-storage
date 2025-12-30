"""API endpoints for retrieving AI-processed book data."""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token, verify_api_key_from_db
from app.db import get_db
from app.repositories.book import BookRepository
from app.repositories.user import UserRepository
from app.schemas.ai_data import (
    AudioUrlResponse,
    ModuleDetailResponse,
    ModuleListResponse,
    ModuleSummary,
    ProcessingMetadataResponse,
    StageResultResponse,
    VocabularyResponse,
    VocabularyWordAudio,
    VocabularyWordResponse,
)
from app.services.ai_data import get_ai_data_retrieval_service

router = APIRouter(prefix="/books", tags=["AI Data"])
_bearer_scheme = HTTPBearer(auto_error=True)
_book_repository = BookRepository()
_user_repository = UserRepository()
logger = logging.getLogger(__name__)

# Supported language codes for audio
SUPPORTED_LANGUAGES = {"en", "tr", "de", "fr", "es", "it", "pt", "ru", "ar", "zh", "ja", "ko"}

# Cache durations in seconds
CACHE_METADATA = 60  # 1 minute for metadata (may change during processing)
CACHE_MODULES = 300  # 5 minutes for modules (relatively static)
CACHE_VOCABULARY = 300  # 5 minutes for vocabulary
CACHE_AUDIO = 3600  # 1 hour for audio URLs


def _require_auth(credentials: HTTPAuthorizationCredentials, db: Session) -> int:
    """Validate JWT token or API key and return user ID or -1 for API key auth."""
    token = credentials.credentials

    # Try JWT first
    try:
        payload = decode_access_token(token, settings=get_settings())
        subject = payload.get("sub")
        if subject is not None:
            try:
                user_id = int(subject)
                user = _user_repository.get(db, user_id)
                if user is not None:
                    return user_id
            except (TypeError, ValueError):
                pass
    except ValueError:
        pass  # JWT failed, try API key

    # Try API key
    api_key_info = verify_api_key_from_db(token, db)
    if api_key_info is not None:
        return -1  # API key authentication

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
    )


def _get_book_info(db: Session, book_id: int) -> tuple[str, str]:
    """Get publisher name and book name for a book ID.

    Returns:
        Tuple of (publisher_name, book_name)

    Raises:
        HTTPException 404 if book not found
    """
    book = _book_repository.get_by_id(db, book_id)
    if book is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )
    return book.publisher, book.book_name


# =============================================================================
# Metadata Endpoint
# =============================================================================


@router.get(
    "/{book_id}/ai-data/metadata",
    response_model=ProcessingMetadataResponse,
)
def get_ai_metadata(
    book_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get AI processing metadata for a book.

    Returns metadata about the AI processing status, including:
    - Processing status and timestamps
    - Total pages, modules, vocabulary, and audio files
    - Language and difficulty information
    - Stage completion status

    Args:
        book_id: ID of the book

    Returns:
        ProcessingMetadataResponse with metadata

    Raises:
        401: Invalid authentication
        404: Book not found or not processed
    """
    _require_auth(credentials, db)
    publisher, book_name = _get_book_info(db, book_id)

    retrieval_service = get_ai_data_retrieval_service()
    metadata = retrieval_service.get_metadata(publisher, str(book_id), book_name)

    if metadata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI data not found for this book",
        )

    # Convert stages to response format
    stages_response = {}
    for stage_name, stage_result in metadata.stages.items():
        stages_response[stage_name] = StageResultResponse(
            status=stage_result.status.value,
            completed_at=stage_result.completed_at.isoformat() if stage_result.completed_at else None,
            error_message=stage_result.error_message if stage_result.error_message else None,
        )

    response_data = ProcessingMetadataResponse(
        book_id=metadata.book_id,
        processing_status=metadata.processing_status.value,
        processing_started_at=metadata.processing_started_at.isoformat() if metadata.processing_started_at else None,
        processing_completed_at=metadata.processing_completed_at.isoformat() if metadata.processing_completed_at else None,
        total_pages=metadata.total_pages,
        total_modules=metadata.total_modules,
        total_vocabulary=metadata.total_vocabulary,
        total_audio_files=metadata.total_audio_files,
        languages=metadata.languages,
        primary_language=metadata.primary_language,
        difficulty_range=metadata.difficulty_range,
        stages=stages_response,
        errors=metadata.errors,
    )

    response = JSONResponse(content=response_data.model_dump())
    response.headers["Cache-Control"] = f"public, max-age={CACHE_METADATA}"
    return response


# =============================================================================
# Modules Endpoints
# =============================================================================


@router.get(
    "/{book_id}/ai-data/modules",
    response_model=ModuleListResponse,
)
def list_ai_modules(
    book_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """List all modules for a book.

    Returns a list of module summaries with module_id, title, pages, and word_count.

    Args:
        book_id: ID of the book

    Returns:
        ModuleListResponse with list of modules

    Raises:
        401: Invalid authentication
        404: Book not found or no modules found
    """
    _require_auth(credentials, db)
    publisher, book_name = _get_book_info(db, book_id)

    retrieval_service = get_ai_data_retrieval_service()
    modules = retrieval_service.list_modules(publisher, str(book_id), book_name)

    if modules is None or len(modules) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No modules found for this book",
        )

    # Build module summaries
    module_summaries = [
        ModuleSummary(
            module_id=m.get("module_id", 0),
            title=m.get("title", ""),
            pages=m.get("pages", []),
            word_count=m.get("word_count", 0),
        )
        for m in modules
    ]

    response_data = ModuleListResponse(
        book_id=str(book_id),
        total_modules=len(module_summaries),
        modules=module_summaries,
    )

    response = JSONResponse(content=response_data.model_dump())
    response.headers["Cache-Control"] = f"public, max-age={CACHE_MODULES}"
    return response


@router.get(
    "/{book_id}/ai-data/modules/{module_id}",
    response_model=ModuleDetailResponse,
)
def get_ai_module(
    book_id: int,
    module_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get full data for a single module.

    Returns complete module data including text content, topics, and vocabulary IDs.

    Args:
        book_id: ID of the book
        module_id: ID of the module

    Returns:
        ModuleDetailResponse with full module data

    Raises:
        401: Invalid authentication
        404: Book not found or module not found
    """
    _require_auth(credentials, db)
    publisher, book_name = _get_book_info(db, book_id)

    retrieval_service = get_ai_data_retrieval_service()
    module = retrieval_service.get_module(publisher, str(book_id), book_name, module_id)

    if module is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module {module_id} not found",
        )

    response_data = ModuleDetailResponse(
        module_id=module.get("module_id", 0),
        title=module.get("title", ""),
        pages=module.get("pages", []),
        text=module.get("text", ""),
        topics=module.get("topics", []),
        vocabulary_ids=module.get("vocabulary_ids", []),
        language=module.get("language", ""),
        difficulty=module.get("difficulty", ""),
        word_count=module.get("word_count", 0),
        extracted_at=module.get("extracted_at"),
    )

    response = JSONResponse(content=response_data.model_dump())
    response.headers["Cache-Control"] = f"public, max-age={CACHE_MODULES}"
    return response


# =============================================================================
# Vocabulary Endpoint
# =============================================================================


@router.get(
    "/{book_id}/ai-data/vocabulary",
    response_model=VocabularyResponse,
)
def get_ai_vocabulary(
    book_id: int,
    module: int | None = Query(None, description="Filter vocabulary by module ID"),
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get vocabulary data for a book.

    Returns vocabulary words with translations, definitions, and audio references.
    Optionally filter by module ID.

    Args:
        book_id: ID of the book
        module: Optional module ID to filter by

    Returns:
        VocabularyResponse with vocabulary words

    Raises:
        401: Invalid authentication
        404: Book not found or vocabulary not found
    """
    _require_auth(credentials, db)
    publisher, book_name = _get_book_info(db, book_id)

    retrieval_service = get_ai_data_retrieval_service()
    vocabulary = retrieval_service.get_vocabulary(
        publisher, str(book_id), book_name, module_id=module
    )

    if vocabulary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary not found for this book",
        )

    # Build vocabulary word responses
    words = []
    for word_data in vocabulary.get("words", []):
        audio_data = word_data.get("audio")
        audio = None
        if audio_data:
            audio = VocabularyWordAudio(
                word=audio_data.get("word"),
                translation=audio_data.get("translation"),
            )

        words.append(
            VocabularyWordResponse(
                id=word_data.get("id", ""),
                word=word_data.get("word", ""),
                translation=word_data.get("translation", ""),
                definition=word_data.get("definition", ""),
                part_of_speech=word_data.get("part_of_speech", ""),
                level=word_data.get("level", ""),
                example=word_data.get("example", ""),
                module_id=word_data.get("module_id"),
                page=word_data.get("page"),
                audio=audio,
            )
        )

    response_data = VocabularyResponse(
        book_id=str(book_id),
        language=vocabulary.get("language", ""),
        translation_language=vocabulary.get("translation_language", ""),
        total_words=vocabulary.get("total_words", len(words)),
        words=words,
        extracted_at=vocabulary.get("extracted_at"),
    )

    response = JSONResponse(content=response_data.model_dump())
    response.headers["Cache-Control"] = f"public, max-age={CACHE_VOCABULARY}"
    return response


# =============================================================================
# Audio URL Endpoint
# =============================================================================


@router.get(
    "/{book_id}/ai-data/audio/vocabulary/{lang}/{word}.mp3",
    response_model=AudioUrlResponse,
)
def get_vocabulary_audio_url(
    book_id: int,
    lang: str,
    word: str,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Get presigned URL for a vocabulary audio file.

    Generates a presigned URL for downloading the audio pronunciation
    of a vocabulary word. URLs are valid for 1 hour.

    Args:
        book_id: ID of the book
        lang: Language code (e.g., 'en', 'tr')
        word: The vocabulary word

    Returns:
        AudioUrlResponse with presigned URL

    Raises:
        400: Invalid language code
        401: Invalid authentication
        404: Book not found or audio file not found
    """
    _require_auth(credentials, db)

    # Validate language code
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language code: {lang}. Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}",
        )

    # Basic word validation - alphanumeric, hyphens, underscores
    if not re.match(r"^[\w\-]+$", word, re.UNICODE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid word format",
        )

    publisher, book_name = _get_book_info(db, book_id)

    retrieval_service = get_ai_data_retrieval_service()
    expires_in = 3600  # 1 hour

    presigned_url = retrieval_service.get_audio_url(
        publisher=publisher,
        book_id=str(book_id),
        book_name=book_name,
        language=lang,
        word=word,
        expires_in=expires_in,
    )

    if presigned_url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found for word '{word}' in language '{lang}'",
        )

    response_data = AudioUrlResponse(
        word=word,
        language=lang,
        url=presigned_url,
        expires_in=expires_in,
    )

    response = JSONResponse(content=response_data.model_dump())
    response.headers["Cache-Control"] = f"public, max-age={CACHE_AUDIO}"
    return response
