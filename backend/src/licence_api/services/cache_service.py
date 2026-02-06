"""Redis caching service for API response caching."""

import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

import redis.asyncio as redis
from pydantic import BaseModel

from licence_api.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheConfig:
    """Cache configuration with key prefixes."""

    # Cache key prefixes (constant - not configurable)
    PREFIX_DASHBOARD = "dashboard"
    PREFIX_DEPARTMENTS = "departments"
    PREFIX_PROVIDERS = "providers"
    PREFIX_PROVIDER_STATS = "provider_stats"
    PREFIX_LICENSE_STATS = "license_stats"
    PREFIX_PAYMENT_METHODS = "payment_methods"
    PREFIX_SETTINGS = "settings"


def get_cache_ttl(prefix: str) -> int:
    """Get TTL for a cache prefix from settings.

    Args:
        prefix: Cache key prefix

    Returns:
        TTL in seconds
    """
    settings = get_settings()
    ttl_map = {
        CacheConfig.PREFIX_DASHBOARD: settings.cache_ttl_dashboard,
        CacheConfig.PREFIX_DEPARTMENTS: settings.cache_ttl_departments,
        CacheConfig.PREFIX_PROVIDERS: settings.cache_ttl_providers,
        CacheConfig.PREFIX_PROVIDER_STATS: settings.cache_ttl_provider_stats,
        CacheConfig.PREFIX_LICENSE_STATS: settings.cache_ttl_license_stats,
        CacheConfig.PREFIX_PAYMENT_METHODS: settings.cache_ttl_payment_methods,
        CacheConfig.PREFIX_SETTINGS: settings.cache_ttl_settings,
    }
    return ttl_map.get(prefix, 300)  # Default 5 minutes


class CacheService:
    """Service for Redis-based caching of API responses.

    Provides methods for caching and invalidating various data types
    used throughout the application.
    """

    _instance: "CacheService | None" = None
    _client: redis.Redis | None = None

    def __init__(self) -> None:
        """Initialize cache service."""
        self._connected = False

    @classmethod
    async def get_instance(cls) -> "CacheService":
        """Get or create cache service instance.

        Returns:
            CacheService singleton instance
        """
        if cls._instance is None:
            cls._instance = CacheService()
            await cls._instance._connect()
        return cls._instance

    async def _connect(self) -> None:
        """Connect to Redis server."""
        settings = get_settings()

        if not settings.redis_url:
            logger.warning("REDIS_URL not configured - caching disabled")
            return

        # Convert RedisDsn to string for URL manipulation
        redis_url = str(settings.redis_url)

        try:
            # Use database 0 for caching (database 1 is for rate limiting)
            if "/1" in redis_url:
                redis_url = redis_url.replace("/1", "/0")
            elif not redis_url.endswith("/0"):
                if redis_url.endswith("/"):
                    redis_url = f"{redis_url}0"
                else:
                    redis_url = f"{redis_url}/0"

            self._client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info("Redis cache connected successfully")
        except redis.RedisError as e:
            logger.warning("Failed to connect to Redis for caching: %s", e)
            self._client = None
            self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if cache is connected."""
        return self._connected and self._client is not None

    def _make_key(self, prefix: str, *parts: str) -> str:
        """Create a cache key from parts.

        Args:
            prefix: Key prefix
            *parts: Additional key parts

        Returns:
            Formatted cache key
        """
        key_parts = [prefix] + [str(p) for p in parts if p]
        return ":".join(key_parts)

    async def get(self, key: str) -> str | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.is_connected:
            return None

        try:
            return await self._client.get(key)
        except redis.RedisError as e:
            logger.error("Cache get error: %s", e)
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: int | None = None,
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        if not self.is_connected:
            return False

        try:
            if ttl:
                await self._client.setex(key, ttl, value)
            else:
                await self._client.set(key, value)
            return True
        except redis.RedisError as e:
            logger.error("Cache set error: %s", e)
            return False

    async def delete(self, *keys: str) -> int:
        """Delete keys from cache.

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        if not self.is_connected or not keys:
            return 0

        try:
            return await self._client.delete(*keys)
        except redis.RedisError as e:
            logger.error("Cache delete error: %s", e)
            return 0

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "dashboard:*")

        Returns:
            Number of keys deleted
        """
        if not self.is_connected:
            return 0

        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self._client.delete(*keys)
            return 0
        except redis.RedisError as e:
            logger.error("Cache delete pattern error: %s", e)
            return 0

    async def get_json(self, key: str) -> dict | list | None:
        """Get JSON value from cache.

        Args:
            key: Cache key

        Returns:
            Parsed JSON or None
        """
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(
        self,
        key: str,
        value: dict | list | BaseModel,
        ttl: int | None = None,
    ) -> bool:
        """Set JSON value in cache.

        Args:
            key: Cache key
            value: Value to cache (dict, list, or Pydantic model)
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        try:
            if isinstance(value, BaseModel):
                json_str = value.model_dump_json()
            else:
                json_str = json.dumps(value)
            return await self.set(key, json_str, ttl)
        except (redis.RedisError, TypeError, ValueError) as e:
            logger.error("Cache set_json error: %s", e)
            return False

    # Domain-specific cache methods

    async def get_dashboard(self, department: str | None = None) -> dict | None:
        """Get cached dashboard data.

        Args:
            department: Optional department filter

        Returns:
            Cached dashboard data or None
        """
        key = self._make_key(CacheConfig.PREFIX_DASHBOARD, department or "all")
        return await self.get_json(key)

    async def set_dashboard(
        self,
        data: dict | BaseModel,
        department: str | None = None,
    ) -> bool:
        """Cache dashboard data.

        Args:
            data: Dashboard data
            department: Optional department filter

        Returns:
            True if successful
        """
        key = self._make_key(CacheConfig.PREFIX_DASHBOARD, department or "all")
        return await self.set_json(key, data, get_cache_ttl(CacheConfig.PREFIX_DASHBOARD))

    async def invalidate_dashboard(self) -> int:
        """Invalidate all dashboard cache entries.

        Returns:
            Number of keys deleted
        """
        return await self.delete_pattern(f"{CacheConfig.PREFIX_DASHBOARD}:*")

    async def get_departments(self) -> list | None:
        """Get cached departments list.

        Returns:
            Cached departments or None
        """
        key = self._make_key(CacheConfig.PREFIX_DEPARTMENTS)
        return await self.get_json(key)

    async def set_departments(self, data: list) -> bool:
        """Cache departments list.

        Args:
            data: Departments data

        Returns:
            True if successful
        """
        key = self._make_key(CacheConfig.PREFIX_DEPARTMENTS)
        return await self.set_json(key, data, get_cache_ttl(CacheConfig.PREFIX_DEPARTMENTS))

    async def invalidate_departments(self) -> int:
        """Invalidate departments cache.

        Returns:
            Number of keys deleted
        """
        key = self._make_key(CacheConfig.PREFIX_DEPARTMENTS)
        return await self.delete(key)

    async def get_providers(self) -> list | None:
        """Get cached providers list.

        Returns:
            Cached providers or None
        """
        key = self._make_key(CacheConfig.PREFIX_PROVIDERS)
        return await self.get_json(key)

    async def set_providers(self, data: list | BaseModel) -> bool:
        """Cache providers list.

        Args:
            data: Providers data

        Returns:
            True if successful
        """
        key = self._make_key(CacheConfig.PREFIX_PROVIDERS)
        return await self.set_json(key, data, get_cache_ttl(CacheConfig.PREFIX_PROVIDERS))

    async def invalidate_providers(self) -> int:
        """Invalidate providers cache.

        Returns:
            Number of keys deleted
        """
        return await self.delete_pattern(f"{CacheConfig.PREFIX_PROVIDERS}*")

    async def get_payment_methods(self) -> list | None:
        """Get cached payment methods list.

        Returns:
            Cached payment methods or None
        """
        key = self._make_key(CacheConfig.PREFIX_PAYMENT_METHODS)
        return await self.get_json(key)

    async def set_payment_methods(self, data: list) -> bool:
        """Cache payment methods list.

        Args:
            data: Payment methods data

        Returns:
            True if successful
        """
        key = self._make_key(CacheConfig.PREFIX_PAYMENT_METHODS)
        return await self.set_json(key, data, get_cache_ttl(CacheConfig.PREFIX_PAYMENT_METHODS))

    async def invalidate_payment_methods(self) -> int:
        """Invalidate payment methods cache.

        Returns:
            Number of keys deleted
        """
        key = self._make_key(CacheConfig.PREFIX_PAYMENT_METHODS)
        return await self.delete(key)

    async def invalidate_all(self) -> int:
        """Invalidate all caches.

        Returns:
            Number of keys deleted
        """
        count = 0
        count += await self.invalidate_dashboard()
        count += await self.invalidate_departments()
        count += await self.invalidate_providers()
        count += await self.invalidate_payment_methods()
        return count


# Global instance getter
_cache_instance: CacheService | None = None


async def get_cache_service() -> CacheService:
    """Get the cache service instance.

    Returns:
        CacheService singleton instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = await CacheService.get_instance()
    return _cache_instance


def cache_response(
    prefix: str,
    ttl: int = 300,
    key_builder: Callable[..., str] | None = None,
):
    """Decorator for caching function responses.

    Args:
        prefix: Cache key prefix
        ttl: Time-to-live in seconds
        key_builder: Optional function to build cache key from args

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache = await get_cache_service()

            # Build cache key
            if key_builder:
                key = f"{prefix}:{key_builder(*args, **kwargs)}"
            else:
                key = prefix

            # Try to get from cache
            cached = await cache.get_json(key)
            if cached is not None:
                return cached

            # Execute function
            result = await func(*args, **kwargs)

            # Cache the result
            await cache.set_json(key, result, ttl)

            return result

        return wrapper

    return decorator
