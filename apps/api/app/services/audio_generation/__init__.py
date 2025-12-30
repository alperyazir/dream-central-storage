"""Audio generation service for vocabulary pronunciations."""

from app.services.audio_generation.models import (
    AudioFile,
    AudioGenerationError,
    BookAudioResult,
    NoVocabularyFoundError,
    StorageError,
    TTSError,
    WordAudioResult,
)
from app.services.audio_generation.service import (
    AudioGenerationService,
    get_audio_generation_service,
)
from app.services.audio_generation.storage import (
    AudioStorage,
    get_audio_storage,
)

__all__ = [
    # Service
    "AudioGenerationService",
    "get_audio_generation_service",
    # Storage
    "AudioStorage",
    "get_audio_storage",
    # Models
    "AudioFile",
    "WordAudioResult",
    "BookAudioResult",
    # Exceptions
    "AudioGenerationError",
    "TTSError",
    "StorageError",
    "NoVocabularyFoundError",
]
