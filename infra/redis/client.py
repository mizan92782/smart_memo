"""
infra/redis/client.py — Django Redis CacheClient

A prefix-aware, class-based Redis cache client for Django.
Translated from the FastAPI CacheClient pattern at:
    /home/mizan/Authentication-Fastapi/app/infrastructure/redis/client.py

Uses django's cache framework (django-redis backend) instead of aioredis,
making it fully synchronous and compatible with Django ORM.

Pre-configured instances (at bottom of file):
    registration_cache      — prefix: "register"
    password_reset_cache    — prefix: "password_reset"
    token_blacklist_cache   — prefix: "blacklist"
    otp_cooldown_cache      — prefix: "otp_cooldown"
    product_cache           — prefix: "product"
    category_cache          — prefix: "category"
"""
import json
import logging
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)


class CacheClient:
    """
    A prefix-aware Redis cache client using Django's cache framework.

    Every key stored through this client is automatically namespaced with
    the given prefix: "{prefix}:{key}". This prevents key collisions
    across different features.

    Usage:
        # Direct instantiation
        otp_cache = CacheClient(prefix="otp", ttl=300)
        otp_cache.set("user@example.com", {"otp": "123456"})
        data = otp_cache.get("user@example.com")
        otp_cache.delete("user@example.com")

        # Or use pre-configured instances below
        from infra.redis.client import registration_cache
        registration_cache.set(email, registration_data)
    """

    def __init__(self, prefix: str = "", ttl: int = 300):
        """
        Args:
            prefix: Key namespace prefix. E.g., "register", "otp", "blacklist".
            ttl:    Default time-to-live in seconds (default: 300 = 5 minutes).
        """
        self.prefix = prefix
        self.ttl = ttl

    def _key(self, key: str) -> str:
        """Build the full namespaced cache key."""
        return f"{self.prefix}:{key}" if self.prefix else key

    def get(self, key: str) -> Any | None:
        """
        Retrieve a value by key.

        Args:
            key: The logical key (will be prefixed).
        Returns:
            Deserialized Python object, or None if not found or expired.
        """
        try:
            raw = cache.get(self._key(key))
            if raw is None:
                return None
            # Cache values may be stored as JSON strings or native Python objects
            if isinstance(raw, str):
                return json.loads(raw)
            return raw
        except Exception as exc:
            logger.warning("cache_get_error key=%s error=%s", key, str(exc))
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Store a value with optional TTL override.

        Args:
            key:   The logical key (will be prefixed).
            value: Python object to serialize and cache.
            ttl:   Optional TTL in seconds. Defaults to self.ttl.
        """
        try:
            serialized = json.dumps(value, default=str)
            cache.set(self._key(key), serialized, timeout=ttl or self.ttl)
        except Exception as exc:
            logger.warning("cache_set_error key=%s error=%s", key, str(exc))

    def delete(self, key: str) -> None:
        """
        Delete a cached value by key.

        Args:
            key: The logical key (will be prefixed).
        """
        try:
            cache.delete(self._key(key))
        except Exception as exc:
            logger.warning("cache_delete_error key=%s error=%s", key, str(exc))

    def exists(self, key: str) -> bool:
        """
        Check whether a key exists in the cache.

        Args:
            key: The logical key (will be prefixed).
        Returns:
            True if key exists and has not expired, False otherwise.
        """
        try:
            return cache.get(self._key(key)) is not None
        except Exception:
            return False

    def delete_pattern(self, pattern: str) -> None:
        """
        Delete all keys matching a prefix pattern.
        Only works with django-redis backend (not LocMemCache).

        Args:
            pattern: Glob pattern applied after the prefix. E.g., "*" deletes all keys.
        """
        try:
            full_pattern = self._key(pattern)
            # django-redis exposes delete_pattern on the cache client
            if hasattr(cache, 'delete_pattern'):
                cache.delete_pattern(full_pattern)
            else:
                logger.warning(
                    "delete_pattern not supported by current cache backend. "
                    "Use django-redis for full support."
                )
        except Exception as exc:
            logger.warning("cache_delete_pattern_error pattern=%s error=%s", pattern, str(exc))

    def get_or_set(self, key: str, default_fn, ttl: int | None = None) -> Any:
        """
        Return cached value if it exists, otherwise compute, cache, and return it.

        Args:
            key:        The logical key.
            default_fn: A callable that returns the value if cache misses.
            ttl:        Optional TTL override.
        Returns:
            Cached or freshly computed value.
        """
        value = self.get(key)
        if value is not None:
            return value
        value = default_fn()
        if value is not None:
            self.set(key, value, ttl=ttl)
        return value

    def __repr__(self) -> str:
        return f"CacheClient(prefix='{self.prefix}', ttl={self.ttl})"


# ─── Pre-configured Cache Instances ──────────────────────────────────────────
# Import these directly instead of creating new CacheClient instances.

registration_cache    = CacheClient(prefix="register",       ttl=300)   # 5 min — OTP registration flow
password_reset_cache  = CacheClient(prefix="password_reset", ttl=300)   # 5 min — Password reset OTP
token_blacklist_cache = CacheClient(prefix="blacklist",      ttl=86400) # 24 hr — JWT blacklist
otp_cooldown_cache    = CacheClient(prefix="otp_cooldown",   ttl=60)    # 60 sec — Resend OTP cooldown
product_cache         = CacheClient(prefix="product",        ttl=3600)  # 1 hr  — Product data
category_cache        = CacheClient(prefix="category",       ttl=3600)  # 1 hr  — Category data
session_cache         = CacheClient(prefix="session",        ttl=86400) # 24 hr — Session data
