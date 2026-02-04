"""Application configuration."""

import base64
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Minimum entropy for secrets (measured by character diversity)
MIN_SECRET_UNIQUE_CHARS = 16

# Key generation command for documentation (split for line length)
KEY_GEN_CMD = (
    'python -c "import secrets,base64;'
    'print(base64.b64encode(secrets.token_bytes(32)).decode())"'
)


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

        # In production, require SSL/TLS connection (unless connecting to Docker internal network)
        is_docker_internal = "@postgres:" in url or "@localhost:" in url or "@127.0.0.1:" in url
        if self.environment == "production" and not is_docker_internal and "sslmode=" not in url:
            raise ValueError(
                "DATABASE_URL must include sslmode parameter in production "
                "(e.g., sslmode=require or sslmode=verify-full)"
            )

        # Security: Validate JWT secret has sufficient entropy
        if self.environment == "production":
            if len(set(self.jwt_secret)) < MIN_SECRET_UNIQUE_CHARS:
                raise ValueError(
                    f"JWT_SECRET must contain at least {MIN_SECRET_UNIQUE_CHARS} unique characters "
                    "for sufficient entropy. Use a cryptographically random value."
                )

            # Validate encryption key format (should be base64-encoded 32 bytes)
            try:
                decoded_key = base64.b64decode(self.encryption_key)
                if len(decoded_key) < 32:
                    raise ValueError(
                        "ENCRYPTION_KEY must be at least 32 bytes (256 bits) when decoded. "
                        f"Generate with: {KEY_GEN_CMD}"
                    )
            except Exception:
                # If not valid base64 or decoding fails, check raw length
                if len(self.encryption_key) < 32:
                    raise ValueError(
                        "ENCRYPTION_KEY must be at least 32 characters or "
                        f"a base64-encoded 32-byte key. Generate with: {KEY_GEN_CMD}"
                    )

        return self

    @property
    def async_database_url(self) -> str:
        """Get async database URL for SQLAlchemy with asyncpg.

        Converts sslmode parameter to ssl for asyncpg compatibility:
        - sslmode=disable -> ssl=disable
        - sslmode=require -> ssl=require
        """
        url = str(self.database_url)
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        # Convert sslmode to ssl for asyncpg compatibility
        url = url.replace("sslmode=", "ssl=")
        return url

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
