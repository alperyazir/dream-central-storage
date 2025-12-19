"""Pydantic schemas used by the FastAPI application."""

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
from .webhook import (
    WebhookDeliveryLogRead,
    WebhookEventBookData,
    WebhookEventPayload,
    WebhookSubscriptionCreate,
    WebhookSubscriptionRead,
    WebhookSubscriptionUpdate,
)

__all__ = [
    "ApiKeyCreate",
    "ApiKeyCreated",
    "ApiKeyListResponse",
    "ApiKeyRead",
    "AssetFileInfo",
    "AssetTypeInfo",
    "PublisherAssetsResponse",
    "BookBase",
    "BookCreate",
    "BookRead",
    "BookUpdate",
    "PublisherBase",
    "PublisherCreate",
    "PublisherRead",
    "PublisherUpdate",
    "PublisherWithBooks",
    "RestoreRequest",
    "RestoreResponse",
    "TrashEntryRead",
    "LoginRequest",
    "TokenResponse",
    "SessionResponse",
    "WebhookSubscriptionCreate",
    "WebhookSubscriptionRead",
    "WebhookSubscriptionUpdate",
    "WebhookDeliveryLogRead",
    "WebhookEventPayload",
    "WebhookEventBookData",
]
