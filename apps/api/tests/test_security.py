"""Unit tests for core security helpers."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token


def test_decode_access_token_returns_payload() -> None:
    settings = get_settings()
    token = create_access_token(subject="42", settings=settings, expires_delta=timedelta(minutes=5))

    payload = decode_access_token(token, settings=settings)

    assert payload["sub"] == "42"
    assert payload["exp"] > payload["iat"]


def test_decode_access_token_rejects_tampered_signature() -> None:
    settings = get_settings()
    token = create_access_token(subject="42", settings=settings, expires_delta=timedelta(minutes=5))

    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")

    with pytest.raises(ValueError, match="Token signature mismatch"):
        decode_access_token(tampered, settings=settings)


def test_decode_access_token_rejects_expired_token() -> None:
    settings = get_settings()
    token = create_access_token(subject="42", settings=settings, expires_delta=timedelta(seconds=-1))

    with pytest.raises(ValueError, match="Token expired"):
        decode_access_token(token, settings=settings)
