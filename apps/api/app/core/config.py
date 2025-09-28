from functools import lru_cache

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:  # pragma: no cover - exercised only when dependency missing
    from pydantic import BaseModel, ConfigDict

    class BaseSettings(BaseModel):
        """Fallback BaseSettings that mirrors pydantic-settings behaviour for tests."""

        model_config = ConfigDict()


    def SettingsConfigDict(**kwargs: object) -> ConfigDict:
        """Provide a ConfigDict-compatible factory when pydantic-settings is unavailable."""

        return ConfigDict(**kwargs)


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Dream Central Storage API"
    app_version: str = "0.1.0"

    database_scheme: str = "postgresql+psycopg"
    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "dream_admin"
    database_password: str = "dream_password"
    database_name: str = "dream_central"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "dream_minio"
    minio_secret_key: str = "dream_minio_secret"
    minio_secure: bool = False
    minio_books_bucket: str = "books"
    minio_apps_bucket: str = "apps"
    minio_trash_bucket: str = "trash"

    jwt_secret_key: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 30

    cors_allowed_origins: str | list[str] = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DCS_",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """Assemble a SQLAlchemy compatible database URL."""
        return (
            f"{self.database_scheme}://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def minio_buckets(self) -> list[str]:
        """Return the list of buckets the application requires."""

        return [
            self.minio_books_bucket,
            self.minio_apps_bucket,
            self.minio_trash_bucket,
        ]

    @property
    def resolved_cors_allowed_origins(self) -> list[str]:
        """Return the configured CORS origins as a normalized list."""

        if isinstance(self.cors_allowed_origins, str):
            return [
                origin.strip()
                for origin in self.cors_allowed_origins.split(",")
                if origin.strip()
            ]

        return list(self.cors_allowed_origins)


@lru_cache
def get_settings() -> Settings:
    """Cache settings to avoid re-parsing environment files."""
    return Settings()
