---
name: favorites-search
description: Favorite stores, product/store search, filters and efficient result pagination.
---
# Favorites and Search

## Rules
- Enforce a unique customer/store favorite relationship so retries cannot create duplicates.
- Customers can add/remove only their own favorites.
- Product search is scoped to a store or the explicitly supported multi-store search context.
- Search by name, SKU/product ID and barcode only where supported.
- Normalize input safely and use indexed search capabilities appropriate to the database.
- Validate sort/filter fields against an allowlist; never interpolate arbitrary client input into SQL.
- Paginate results with stable ordering and a maximum page size.
- Consider search query length, rate limiting and abuse protection.
- Invalidate or update cached results after relevant catalog changes.

## Acceptance checks
- Repeated favorite requests remain idempotent.
- Cross-customer favorite access is blocked.
- Search cannot leak private products or supplier/cost fields.
- Search/filter combinations have bounded, tested query behavior.

## Verified Implementation Pattern
- **Unique Constraint & Idempotency**: `FavoriteStore` uses `UniqueConstraint(fields=['customer', 'store'], name='unique_customer_store_favorite')`. Repository uses `get_or_create` with soft-deletion awareness (`fav.restore()` if previously soft-deleted) to ensure retry idempotency.
- **Customer Tenant Isolation**: `/stores/favorites/` and `/stores/{id}/favorite/` strictly require `[IsAuthenticated(), IsCustomer()]`. Customer A cannot list, modify, or delete Customer B's favorite records.
- **Eager Loading**: `FavoriteStoreRepository.get_by_customer()` executes `select_related('store', 'store__vendor')` to eliminate N+1 queries during listing.

