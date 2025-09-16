from __future__ import annotations

from pydantic import BaseModel, Field


class S3Config(BaseModel):
    endpoint: str | None = Field(default=None, description="S3/MinIO endpoint, e.g., http://localhost:9000")
    access_key: str | None = Field(default=None, description="S3/MinIO access key")
    secret_key: str | None = Field(default=None, description="S3/MinIO secret key")
    bucket: str | None = Field(default=None, description="Default bucket name for assets")
    secure: bool = Field(default=False, description="Use TLS for the S3 connection")


class AuthConfig(BaseModel):
    bearer_token: str | None = Field(default=None, description="Static bearer token for MVP auth")


def load_s3_config(env: dict[str, str] | None = None) -> S3Config:
    """Load S3 config from environment variables.

    Supported variables:
    - S3_ENDPOINT or MINIO_ENDPOINT
    - S3_ACCESS_KEY or MINIO_ACCESS_KEY
    - S3_SECRET_KEY or MINIO_SECRET_KEY
    - S3_BUCKET or MINIO_BUCKET
    - S3_SECURE ("true"/"false"); defaults to false
    """
    source = env or {}

    def get_any(*keys: str) -> str | None:
        for k in keys:
            if k in source:
                return source[k]
        return None

    # If no explicit env passed, read from process env
    if not source:
        import os

        source = os.environ  # type: ignore[assignment]

    endpoint = get_any("S3_ENDPOINT", "MINIO_ENDPOINT")
    access_key = get_any("S3_ACCESS_KEY", "MINIO_ACCESS_KEY")
    secret_key = get_any("S3_SECRET_KEY", "MINIO_SECRET_KEY")
    bucket = get_any("S3_BUCKET", "MINIO_BUCKET")

    secure_raw = source.get("S3_SECURE")
    secure = str(secure_raw).lower() in {"1", "true", "yes", "on"} if secure_raw is not None else False

    return S3Config(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        bucket=bucket,
        secure=secure,
    )


def load_auth_config(env: dict[str, str] | None = None) -> AuthConfig:
    """Load authentication configuration from environment variables.

    - AUTH_BEARER_TOKEN: static token used for simple bearer validation
    """
    source = env or {}
    if not source:
        import os

        source = os.environ  # type: ignore[assignment]

    token = source.get("AUTH_BEARER_TOKEN")
    return AuthConfig(bearer_token=token)
