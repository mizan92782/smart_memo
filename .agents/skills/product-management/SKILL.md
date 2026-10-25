---
name: product-management
description: Product catalog, identifiers, measurement units, product availability and images.
---
# Product Management

## Rules
- Define SKU/product-ID uniqueness scope explicitly; vendor-specific SKUs usually need uniqueness within a store/tenant, not globally.
- Model product identity separately from store-specific price and stock if the domain needs a shared catalog; otherwise document the simpler store-owned model.
- Validate positive prices, supported unit, name, category ownership and quantity precision.
- Support piece, weight, volume, packet/box and configurable units only with explicit rules.
- Do not assume every unit is convertible. Store conversion factors only for compatible dimensions and define a base unit.
- Store product images through the project's approved upload/storage path; validate file type, size and access.
- Search must be tenant/store scoped and must not reveal private products.
- Index barcode fields (`db_index=True`) for sub-millisecond in-store shelf barcode scanning (`/products/api/barcode-lookup/`).
- Fallback barcode resolution to SKU if barcode is not set or matches store SKU.
- Preserve order-item snapshots so catalog edits do not rewrite historical purchases.

## Acceptance checks
- Invalid unit/quantity combinations are rejected.
- Duplicate identifiers follow the documented uniqueness rule.
- Product search and category filtering are scoped and paginated.
- Barcode lookups enforce store tenant isolation (barcodes from other stores return 404).

## Verified Architecture Patterns
- **Multi-Photo Gallery & Primary Showcase**: Products support multiple gallery photos via `ProductImage` (`product`, `image`, `image_url`, `is_primary`, `display_order`, `alt_text`).
- **Primary Image Invariant**: When a `ProductImage` is saved with `is_primary=True`, all other images for that product automatically have `is_primary` unset.
- **N+1 Prevention with Prefetched Cache**: `Product.primary_image_url` property checks `_prefetched_objects_cache['images']` first. If present, it computes the primary URL in-memory without issuing per-row SQL queries.
- **Catalog Prefetching**: `ProductRepository.search_catalog` and `ProductViewSet.get_queryset` prefetch `images` (`prefetch_related('images')`), maintaining strictly constant O(1) query complexity.
- **Tenant Isolation on Photo Mutations**: Adding, deleting, or setting primary image requires vendor ownership of the store containing the product (`GET` is public, mutations require `[IsAuthenticated, IsVendor]` and ownership check).
