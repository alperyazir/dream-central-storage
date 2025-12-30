"""Pydantic schemas used by the FastAPI application."""

from .ai_data import (
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
from .api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyListResponse, ApiKeyRead
from .asset import AssetFileInfo, AssetTypeInfo, PublisherAssetsResponse
from .auth import LoginRequest, SessionResponse, TokenResponse
from .book import BookBase, BookCreate, BookRead, BookUpdate
from .publisher import (
    PublisherBase,
    PublisherCreate,
    PublisherRead,
    PublisherUpdate,
    PublisherWithBooks,
)
from .storage import RestoreRequest, RestoreResponse, TrashEntryRead
from .processing import (
    CleanupStatsResponse,
    ProcessingJobResponse,
    ProcessingStatusResponse,
    ProcessingTriggerRequest,
    QueueStatsResponse,
)
from .webhook import (
    WebhookDeliveryLogRead,
    WebhookEventBookData,
    WebhookEventPayload,
    WebhookSubscriptionCreate,
    WebhookSubscriptionRead,
    WebhookSubscriptionUpdate,
)

__all__ = [
    # AI Data schemas
    "AudioUrlResponse",
    "ModuleDetailResponse",
    "ModuleListResponse",
    "ModuleSummary",
    "ProcessingMetadataResponse",
    "StageResultResponse",
    "VocabularyResponse",
    "VocabularyWordAudio",
    "VocabularyWordResponse",
    # API Key schemas
    "ApiKeyCreate",
    "ApiKeyCreated",
    "ApiKeyListResponse",
    "ApiKeyRead",
    # Asset schemas
    "AssetFileInfo",
    "AssetTypeInfo",
    "PublisherAssetsResponse",
    # Book schemas
    "BookBase",
    "BookCreate",
    "BookRead",
    "BookUpdate",
    # Processing schemas
    "CleanupStatsResponse",
    "ProcessingJobResponse",
    "ProcessingStatusResponse",
    "ProcessingTriggerRequest",
    "QueueStatsResponse",
    # Publisher schemas
    "PublisherBase",
    "PublisherCreate",
    "PublisherRead",
    "PublisherUpdate",
    "PublisherWithBooks",
    # Storage schemas
    "RestoreRequest",
    "RestoreResponse",
    "TrashEntryRead",
    # Auth schemas
    "LoginRequest",
    "TokenResponse",
    "SessionResponse",
    # Webhook schemas
    "WebhookSubscriptionCreate",
    "WebhookSubscriptionRead",
    "WebhookSubscriptionUpdate",
    "WebhookDeliveryLogRead",
    "WebhookEventPayload",
    "WebhookEventBookData",
]
