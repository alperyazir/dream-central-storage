"""Pydantic schemas for authentication workflows."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials payload submitted to the login endpoint."""

    email: str = Field(..., max_length=320)
    password: str


class TokenResponse(BaseModel):
    """JWT token response returned to the caller."""

    access_token: str
    token_type: str = "bearer"
