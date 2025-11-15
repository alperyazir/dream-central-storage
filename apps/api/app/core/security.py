"""Security helpers for password hashing and JWT generation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt

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


# API Key Management


def generate_api_key(environment: str, service: str) -> str:
    """Generate a new API key with the format: dcs_{environment}_{service}_{24_random_chars}."""
    random_part = secrets.token_urlsafe(24)[:24]
    return f"dcs_{environment}_{service}_{random_part}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key using bcrypt."""
    return bcrypt.hashpw(api_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Verify an API key against the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(api_key.encode("utf-8"), stored_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def get_api_key_prefix(api_key: str) -> str:
    """Extract the first 16 characters of the API key for display purposes."""
    return api_key[:16] if len(api_key) >= 16 else api_key


def authenticate_token_or_api_key(token: str, settings: Settings | None = None) -> dict[str, Any]:
    """
    Authenticate a request using either JWT token or API key.

    Returns a dict with authentication info:
    - For JWT: {"type": "jwt", "user_id": int}
    - For API key: {"type": "api_key", "api_key_id": int}

    Raises ValueError if authentication fails.
    """
    active_settings = settings or get_settings()

    # Try JWT first
    try:
        payload = decode_access_token(token, settings=active_settings)
        subject = payload.get("sub")
        if subject is not None:
            return {"type": "jwt", "user_id": int(subject), "payload": payload}
    except ValueError:
        pass  # JWT failed, try API key

    # If JWT fails, it might be an API key
    # We need to check the database for the API key
    # This will be done in the router/dependency level where we have DB access
    raise ValueError("Authentication required - token is neither valid JWT nor API key format")


def verify_api_key_from_db(token: str, session) -> dict[str, Any] | None:
    """
    Verify if the token is a valid API key by checking the database.

    Returns dict with api_key info if valid, None otherwise.
    This function is meant to be called from routers that have DB session access.
    """
    from datetime import datetime, timezone
    from app.repositories.api_key import ApiKeyRepository

    repository = ApiKeyRepository()

    # Try to find an API key that matches
    # We need to check all API keys and verify with bcrypt
    # This is not efficient, but for now we'll iterate through active keys
    # A better approach would be to extract a deterministic prefix, but bcrypt doesn't support that

    # For now, let's get all active API keys and check each one
    api_keys = repository.list_all_keys(session)

    for api_key in api_keys:
        if not api_key.is_active:
            continue

        # Check if expired
        if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
            continue

        # Verify the key
        if verify_api_key(token, api_key.key_hash):
            # Update last_used_at
            repository.update_last_used(session, api_key)
            session.commit()

            return {
                "type": "api_key",
                "api_key_id": api_key.id,
                "api_key": api_key,
            }

    return None
