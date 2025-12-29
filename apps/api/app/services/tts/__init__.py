"""TTS Provider abstraction layer for audio generation."""

from app.services.tts.base import (
    ALTERNATIVE_VOICES,
    VOICE_MAPPING,
    TTSAuthError,
    TTSBatchItem,
    TTSBatchResult,
    TTSConnectionError,
    TTSProvider,
    TTSProviderError,
    TTSProviderType,
    TTSRateLimitError,
    TTSRequest,
    TTSResponse,
    TTSVoice,
    TTSVoiceNotFoundError,
    get_default_voice,
)
from app.services.tts.azure import AzureTTSProvider
from app.services.tts.edge import EdgeTTSProvider
from app.services.tts.service import TTSService, get_tts_service

__all__ = [
    # Service
    "TTSService",
    "get_tts_service",
    # Providers
    "TTSProvider",
    "TTSProviderType",
    "EdgeTTSProvider",
    "AzureTTSProvider",
    # Voice mapping
    "VOICE_MAPPING",
    "ALTERNATIVE_VOICES",
    "get_default_voice",
    # Data models
    "TTSVoice",
    "TTSRequest",
    "TTSResponse",
    "TTSBatchItem",
    "TTSBatchResult",
    # Exceptions
    "TTSProviderError",
    "TTSRateLimitError",
    "TTSAuthError",
    "TTSConnectionError",
    "TTSVoiceNotFoundError",
]
