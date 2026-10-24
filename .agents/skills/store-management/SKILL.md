---
name: store-management
description: Vendor store profile, location, opening hours, delivery settings and store lifecycle.
---
# Store Management

## Rules
- Define store ownership and whether vendors may own multiple stores.
- Validate name, contact details, address, coordinates, opening hours and delivery configuration.
- Keep active/inactive state explicit; inactive stores should not appear as orderable unless policy allows it.
- Store location coordinates with validated latitude/longitude ranges.
- Keep customer-visible store profile fields separate from internal vendor metadata.
- Define safe archival/deactivation behavior for stores with historical orders.
- Every mutation must verify store ownership or delegated permission.

## Workflow
1. Define store model and ownership.
2. Add validation and migration.
3. Implement authorized CRUD and public detail/catalog views.
4. Add store status and opening-hours rules.
5. Test tenant access and customer discovery behavior.

## Acceptance checks
- Unauthorized vendors cannot modify a store.
- Historical orders remain readable after store deactivation.
- Invalid coordinates and malformed opening hours are rejected.

## Verified Architecture Patterns
- **Store Verification & Compliance**: Stores have explicit verification fields (`is_verified`, `verified_at`, `verification_notes`). Only `STAFF` and `SUPERUSER` roles can verify or suspend stores.
- **Vendor Read-Only Protection**: Make `is_verified`, `verified_at`, and `verification_notes` read-only in `StoreSerializer` so vendors cannot self-verify.
- **Discovery & Checkout Guard**: Both `get_public_active_stores()` and `submit_order_from_card` enforce `is_active=True and is_verified=True`. Suspended or unverified stores are hidden from public searches and reject new orders.
- **Platform-Wide Governance Aggregations**: Staff and Superusers can query `GET /stores/governance-overview/` which computes platform metrics (stores breakdown, user distribution, GMV, orders status) via SQL aggregations (`Count`, `Sum`, `Coalesce`).

