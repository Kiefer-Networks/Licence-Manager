"""Rate limiting configuration for security-sensitive endpoints."""

import os
from ipaddress import ip_address, ip_network
from typing import Sequence

from slowapi import Limiter
from slowapi.util import get_remote_address

from licence_api.config import get_settings


def _get_trusted_proxies() -> Sequence[str]:
    """Get list of trusted proxy IP ranges from environment.

    Returns:
        List of IP addresses or CIDR ranges that are trusted proxies.
    """
    proxies_env = os.environ.get("TRUSTED_PROXIES", "")
    if not proxies_env:
        # Default: trust localhost and common private ranges for development
        settings = get_settings()
        if settings.environment == "development":
            return ["127.0.0.1", "::1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        # In production, require explicit configuration
        return []
    return [p.strip() for p in proxies_env.split(",") if p.strip()]


def _is_trusted_proxy(client_ip: str, trusted_proxies: Sequence[str]) -> bool:
    """Check if client IP is from a trusted proxy.

    Args:
        client_ip: The IP address to check.
        trusted_proxies: List of trusted IP addresses or CIDR ranges.

    Returns:
        True if the IP is trusted.
    """
    if not trusted_proxies:
        return False

    try:
        addr = ip_address(client_ip)
        for proxy in trusted_proxies:
            if "/" in proxy:
                # CIDR range
                if addr in ip_network(proxy, strict=False):
                    return True
            else:
                # Single IP
                if addr == ip_address(proxy):
                    return True
    except ValueError:
        # Invalid IP format
        return False

    return False


def get_real_client_ip(request) -> str:
    """Extract real client IP, handling reverse proxy headers securely.

    Only trusts X-Forwarded-For from configured trusted proxies.
    In production, ensure reverse proxy is properly configured.

    Args:
        request: The incoming request object.

    Returns:
        The client IP address.
    """
    direct_ip = get_remote_address(request)
    trusted_proxies = _get_trusted_proxies()

    # Only trust forwarded headers if request comes from a trusted proxy
    if _is_trusted_proxy(direct_ip, trusted_proxies):
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (client IP) from the chain
            client_ip = forwarded_for.split(",")[0].strip()
            # Validate it's a valid IP format
            try:
                ip_address(client_ip)
                return client_ip
            except ValueError:
                pass

        # Also check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            try:
                ip_address(real_ip)
                return real_ip
            except ValueError:
                pass

    # Fall back to direct client address
    return direct_ip


def _get_storage_uri() -> str | None:
    """Get rate limiter storage URI.

    Uses Redis in production for distributed rate limiting.

    Returns:
        Redis URI or None for in-memory storage.
    """
    settings = get_settings()

    # Always use Redis if REDIS_URL is set
    redis_url = os.environ.get("REDIS_URL")
    if redis_url:
        # Append database index for rate limiting to avoid conflicts
        if redis_url.endswith("/"):
            return f"{redis_url}1"
        elif "/0" in redis_url or redis_url.count("/") == 2:
            # Already has database specified
            return redis_url
        else:
            return f"{redis_url}/1"

    # In production, require Redis
    if settings.environment == "production":
        raise ValueError(
            "REDIS_URL must be configured in production for distributed rate limiting."
        )

    # Development: use in-memory storage
    return None


# Create limiter instance with Redis backend for distributed deployments
limiter = Limiter(
    key_func=get_real_client_ip,
    default_limits=["100/minute"],
    storage_uri=_get_storage_uri(),
)

# Rate limit constants for different endpoint types
AUTH_LOGIN_LIMIT = "5/minute"
AUTH_REFRESH_LIMIT = "10/minute"
AUTH_PASSWORD_CHANGE_LIMIT = "3/minute"
AUTH_LOGOUT_LIMIT = "10/minute"
API_DEFAULT_LIMIT = "100/minute"
