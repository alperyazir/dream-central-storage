"""Pydantic schemas for API key management."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    """Request payload for creating a new API key."""

    name: str = Field(..., max_length=255, description="Human-readable name for the API key")
    description: Optional[str] = Field(None, description="Optional description of the key's purpose")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration timestamp")
    rate_limit: int = Field(100, description="Requests per minute limit")


class ApiKeyCreated(BaseModel):
    """Response returned when an API key is successfully created."""

    id: int
    key: str = Field(..., description="The full API key - shown only once")
    name: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool


class ApiKeyRead(BaseModel):
    """Response for listing API keys (without the actual key)."""

    id: int
    key_prefix: str = Field(..., description="First 16 characters of the key")
    name: str
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    is_active: bool
    rate_limit: int


class ApiKeyListResponse(BaseModel):
    """Response for listing all API keys."""

    api_keys: list[ApiKeyRead]
