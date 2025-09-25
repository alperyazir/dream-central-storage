"""Security helpers for password hashing and JWT generation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import Settings, get_settings

_PASSWORD_SCHEME = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 120_000


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_password_hash(password: str) -> str:
    """Hash a password using PBKDF2-HMAC (SHA-256)."""

    if not password:
        raise ValueError("Password must not be empty")

    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS
    )
    return (
        f"{_PASSWORD_SCHEME}${_PASSWORD_ITERATIONS}$"
        f"{_b64encode(salt)}${_b64encode(derived_key)}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """Validate a password against the stored PBKDF2 hash."""

    try:
        scheme, iteration_str, salt_b64, hash_b64 = stored_hash.split("$")
        if scheme != _PASSWORD_SCHEME:
            return False
        iterations = int(iteration_str)
        salt = _b64decode(salt_b64)
        expected = _b64decode(hash_b64)
    except (ValueError, TypeError):  # pragma: no cover - defensive
        return False

    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(derived, expected)


def create_access_token(
    *,
    subject: str,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
    additional_claims: dict[str, Any] | None = None,
) -> str:
    """Generate a signed JWT for the provided subject."""

    active_settings = settings or get_settings()
    algorithm = active_settings.jwt_algorithm
    now = datetime.now(timezone.utc)
    expires = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=active_settings.jwt_access_token_expires_minutes)
    )

    header = {"alg": algorithm, "typ": "JWT"}
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    if additional_claims:
        payload.update(additional_claims)

    header_segment = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(
        active_settings.jwt_secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    signature_segment = _b64encode(signature)

    return f"{header_segment}.{payload_segment}.{signature_segment}"


def decode_access_token(
    token: str, *, settings: Settings | None = None
) -> dict[str, Any]:
    """Decode and validate a JWT created by ``create_access_token``."""

    active_settings = settings or get_settings()
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Token structure invalid")

    header_segment, payload_segment, signature_segment = parts
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = hmac.new(
        active_settings.jwt_secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    provided_signature = _b64decode(signature_segment)
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise ValueError("Token signature mismatch")

    try:
        payload_data = json.loads(_b64decode(payload_segment))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise ValueError("Token payload malformed") from exc

    exp = payload_data.get("exp")
    if exp is None:
        raise ValueError("Token missing expiration")
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts >= int(exp):
        raise ValueError("Token expired")

    return payload_data
