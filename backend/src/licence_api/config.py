"""Application configuration."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, model_validator
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
    session_cookie_samesite: Literal["lax", "strict", "none"] = "strict"

    # CORS settings
    cors_origins: str = "http://localhost:3000"  # Comma-separated list

    # Trusted proxies for rate limiting (comma-separated IP/CIDR ranges)
    trusted_proxies: str = ""

    # Rate limiting settings (requests per minute unless otherwise noted)
    rate_limit_default: int = 100
    rate_limit_auth_login: int = 5
    rate_limit_auth_refresh: int = 10
    rate_limit_auth_password_change: int = 3
    rate_limit_auth_logout: int = 10
    rate_limit_admin_user_create: int = 10
    rate_limit_admin_role_modify: int = 20
    rate_limit_provider_test: int = 10
    rate_limit_sensitive: int = 5

    # Cache TTL settings (in seconds)
    cache_ttl_dashboard: int = 300  # 5 minutes
    cache_ttl_departments: int = 3600  # 1 hour
    cache_ttl_providers: int = 300  # 5 minutes
    cache_ttl_provider_stats: int = 300  # 5 minutes
    cache_ttl_license_stats: int = 300  # 5 minutes
    cache_ttl_payment_methods: int = 1800  # 30 minutes
    cache_ttl_settings: int = 3600  # 1 hour

    # Audit settings
    audit_retention_days: int = 365  # How long to keep audit logs

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        """Validate settings for security requirements."""
        # Security: Prevent debug mode in production
        if self.environment == "production" and self.debug:
            raise ValueError(
                "DEBUG mode cannot be enabled in production environment. "
                "This would expose API documentation and detailed error messages."
            )

        # Validate database URL format
        url = str(self.database_url)

        # Ensure PostgreSQL URL format
        if not url.startswith(("postgresql://", "postgres://")):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL URL starting with 'postgresql://' or 'postgres://'"
            )

        # In production, require SSL/TLS connection
        if self.environment == "production" and "sslmode=" not in url:
            raise ValueError(
                "DATABASE_URL must include sslmode parameter in production "
                "(e.g., sslmode=require or sslmode=verify-full)"
            )

        return self

    @property
    def async_database_url(self) -> str:
        """Get async database URL for SQLAlchemy."""
        url = str(self.database_url)
        return url.replace("postgresql://", "postgresql+asyncpg://")

    @property
    def google_oauth_enabled(self) -> bool:
        """Check if Google OAuth is configured."""
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def trusted_proxies_list(self) -> list[str]:
        """Get trusted proxies as a list."""
        if not self.trusted_proxies:
            return []
        return [proxy.strip() for proxy in self.trusted_proxies.split(",") if proxy.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
