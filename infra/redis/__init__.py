"""
infra/redis/__init__.py — Redis Infrastructure Package

Exports all pre-configured CacheClient instances.

Usage:
    from infra.redis import registration_cache, otp_cooldown_cache

    # Store OTP data
    registration_cache.set(email, {"otp": hashed_otp, "email": email}, ttl=300)

    # Retrieve OTP data
    data = registration_cache.get(email)

    # Delete after use
    registration_cache.delete(email)
"""
from infra.redis.client import (
    CacheClient,
    registration_cache,
    password_reset_cache,
    token_blacklist_cache,
    otp_cooldown_cache,
    product_cache,
    category_cache,
    session_cache,
)

__all__ = [
    "CacheClient",
    "registration_cache",
    "password_reset_cache",
    "token_blacklist_cache",
    "otp_cooldown_cache",
    "product_cache",
    "category_cache",
    "session_cache",
]
