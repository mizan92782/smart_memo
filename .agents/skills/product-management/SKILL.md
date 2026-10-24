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
