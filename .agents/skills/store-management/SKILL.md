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
- **Verified Customer Reviews**: Customers can submit reviews (`rating` 1-5, `comment`) for stores only if they have at least one verified `COMPLETED` order (`Order.objects.filter(customer=user, store=store, status=OrderStatus.COMPLETED).exists()`).
- **Anti-Spam & Invariant**: Single review per customer per store enforced by unique constraints (`unique_together = ('store', 'customer')`).
- **Instant O(1) Public Ratings**: Stores maintain `average_rating` (`DecimalField(max_digits=3, decimal_places=2)`) and `total_reviews` (`IntegerField`), recalculated via SQL aggregations (`Avg('rating')`, `Count('id')`) upon review creation, update, or deletion. Public discovery and listings read this directly in O(1) time without expensive subqueries.
- **Vendor Response**: Store owners can submit an official reply (`vendor_reply`, `vendor_replied_at`) to reviews on their store (`POST /stores/reviews/{id}/reply/`).
- **Review Deletion & Invalidation**: Customers can delete their own reviews and staff can moderate reviews (`DELETE /stores/reviews/{id}/`), automatically triggering store rating recalculation and cache invalidation (`CacheService.invalidate_store_profile`).
- **Public Store Branding & Standalone Merchant Website URLs**:
  - Stores maintain comprehensive public branding assets: `owner_name`, `logo_url`, `cover_photo_url`, `secondary_phone`, `whatsapp_number`, `website_url`, `social_links`, and `shop_type` (`hybrid`, `physical_only`, `online_only`).
  - Stores automatically generate a `public_url_slug` (e.g., `store-name.com` or custom vanity domain slug) on save.
  - Public resolver `GET /stores/public-store/{slug_or_domain}/` resolves stores by vanity domain (`shopname.com`), bare slug (`shopname`), or store ID with tenant caching.
  - Returns complete merchant website package: store branding, contact channels, live open/closed status, categories, and products with pre-fetched multi-image galleries.
  - Frontend renders standalone merchant web store at `/Eshopping/:storeSlug` with one-click URL copy, WhatsApp integration, and direct memo adding.

