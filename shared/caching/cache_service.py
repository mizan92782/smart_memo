import hashlib
import json
import logging
from typing import Any, Optional
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CacheService:
    """
    Tenant-aware caching service with O(1) versioned invalidation.
    Never caches private responses, user sessions, draft memos, or authoritative checkout.
    """
    DEFAULT_TTL = 300  # 5 minutes

    @staticmethod
    def get_tenant_version(store_id: int | str, namespace: str = "catalog") -> int:
        """Returns the current cache version for a store namespace."""
        version_key = f"version:{namespace}:store:{store_id}"
        try:
            ver = cache.get(version_key)
            if ver is None:
                ver = 1
                cache.set(version_key, ver, timeout=86400 * 30)
            return ver
        except Exception as exc:
            logger.warning("Cache access failed for version key %s: %s", version_key, exc)
            return 1

    @staticmethod
    def invalidate_tenant_namespace(store_id: int | str, namespace: str = "catalog") -> int:
        """
        O(1) version bump invalidating all cached data for this store namespace
        without expensive or blocked KEY scans in Redis.
        """
        version_key = f"version:{namespace}:store:{store_id}"
        try:
            try:
                new_ver = cache.incr(version_key)
            except Exception:
                current = cache.get(version_key) or 1
                new_ver = current + 1
                cache.set(version_key, new_ver, timeout=86400 * 30)
            return new_ver
        except Exception as exc:
            logger.warning("Cache invalidation failed for %s: %s", version_key, exc)
            return 0

    @staticmethod
    def build_cache_key(
        store_id: int | str,
        namespace: str,
        identifier: str,
        params: Optional[dict] = None
    ) -> str:
        """
        Builds a versioned, tenant-isolated cache key.
        e.g. `smartmemo:store:5:catalog:v3:product_list:md5hash`
        """
        version = CacheService.get_tenant_version(store_id, namespace)
        param_hash = ""
        if params:
            sorted_params = json.dumps(params, sort_keys=True, default=str)
            param_hash = ":" + hashlib.md5(sorted_params.encode('utf-8')).hexdigest()[:8]
        return f"smartmemo:store:{store_id}:{namespace}:v{version}:{identifier}{param_hash}"

    @staticmethod
    def get(key: str) -> Any:
        try:
            return cache.get(key)
        except Exception as exc:
            logger.warning("Cache get error for key %s: %s", key, exc)
            return None

    @staticmethod
    def set(key: str, value: Any, timeout: int = DEFAULT_TTL) -> bool:
        try:
            cache.set(key, value, timeout=timeout)
            return True
        except Exception as exc:
            logger.warning("Cache set error for key %s: %s", key, exc)
            return False

    @staticmethod
    def delete(key: str) -> bool:
        try:
            cache.delete(key)
            return True
        except Exception as exc:
            logger.warning("Cache delete error for key %s: %s", key, exc)
            return False

    # Convenience invalidation shortcuts
    @classmethod
    def invalidate_catalog(cls, store_id: int | str) -> int:
        return cls.invalidate_tenant_namespace(store_id, "catalog")

    @classmethod
    def invalidate_store_profile(cls, store_id: int | str) -> int:
        return cls.invalidate_tenant_namespace(store_id, "store")
