---
name: caching
description: Safe cache design, tenant-aware keys, TTLs and invalidation.
---
# Caching

## Rules
- Measure before caching; prefer correctness over speculative optimization.
- Define key format, TTL, invalidation triggers, and acceptable staleness for every cache.
- Include tenant/store, locale, filter, sort, page/cursor and authorization context where those affect the result.
- Never cache private responses under a shared public key.
- Invalidate/update affected keys after product, category, price, offer, store-status or relevant permission changes.
- Checkout must revalidate authoritative price, offer and stock against the database/business service.
- Use a shared cache if multiple app instances require consistent behavior.
- Avoid cache stampedes for expensive hot keys when justified.
- Fail safely if cache is unavailable; cache failure must not corrupt transactional data.

## Acceptance checks
- A write cannot leave incorrect catalog data cached indefinitely.
- One tenant cannot receive another tenant's cached data.
- Checkout does not rely on stale cache for financial or stock correctness.

## Implementation Architecture
- **Service**: `shared/caching/cache_service.py` (`CacheService`)
- **Key Pattern**: `smartmemo:store:{store_id}:{namespace}:v{version}:{identifier}:{param_hash}`
- **O(1) Namespace Invalidation**:
  `version:{namespace}:store:{store_id}` key tracks current version. Calling `invalidate_tenant_namespace` / `invalidate_catalog` / `invalidate_store_profile` performs an atomic `cache.incr()`, rendering all stale keys obsolete in $O(1)$ time without scanning or flushing Redis.
- **Fail-Safe Fallback**:
  All cache calls (`get`, `set`, `delete`) are wrapped in safe exception handling with log warnings, ensuring app operations proceed uninterrupted if cache is down.
- **Authoritative Invariants**:
  Order checkout, reservations, and payment collections bypass all caches and query PostgreSQL directly with row locks (`select_for_update`).

