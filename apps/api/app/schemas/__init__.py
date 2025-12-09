"""Pydantic schemas used by the FastAPI application."""

from .api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyListResponse, ApiKeyRead
from .auth import LoginRequest, SessionResponse, TokenResponse
from .book import BookBase, BookCreate, BookRead, BookUpdate
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
    "BookBase",
    "BookCreate",
    "BookRead",
    "BookUpdate",
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
