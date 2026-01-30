"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Licence Management API"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Database (required - no default for security)
    database_url: PostgresDsn = Field(
        description="PostgreSQL connection URL. Must be set via environment variable."
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379")

    # Security - Encryption
    # Primary encryption key (current key for new encryptions)
    encryption_key: str = Field(min_length=32)
    # Legacy keys for decryption during key rotation (comma-separated, oldest to newest)
    # Example: "old_key_1,old_key_2" when rotating from key 1 -> 2 -> current
    encryption_key_legacy: str = ""

    # Security - JWT
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 1  # Short-lived access tokens
    jwt_issuer: str = "licence-api"
    jwt_audience: str = "licence-app"

    # Security - Refresh Tokens
    refresh_token_days: int = 30

    # Security - Password Policy
    password_min_length: int = 12
    password_history_count: int = 5
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30

    # Google OAuth (optional for local-only auth)
    google_client_id: str = ""
    google_client_secret: str = ""

    # Optional domain restriction
    allowed_email_domain: str | None = None

    # Sync settings
    sync_interval_minutes: int = 60

    # Session settings
    session_cookie_name: str = "licence_session"
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    @property
    def async_database_url(self) -> str:
        """Get async database URL for SQLAlchemy."""
        url = str(self.database_url)
        return url.replace("postgresql://", "postgresql+asyncpg://")

    @property
    def google_oauth_enabled(self) -> bool:
        """Check if Google OAuth is configured."""
        return bool(self.google_client_id and self.google_client_secret)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
