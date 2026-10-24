---
name: pricing-offers
description: Product pricing, discounts, offer validity, and authoritative totals.
---
# Pricing and Offers

## Rules
- Calculate all authoritative totals on the server.
- Use decimal or integer minor units for money, never binary floating point.
- Define whether discounts are fixed amount, percentage, or tiered; validate limits and rounding.
- Validate start/end timestamps, activation, eligible products, quantity constraints and stacking rules.
- Snapshot unit price, applied discount, tax/fees where relevant, and line total into the order item at submission/acceptance according to policy.
- Revalidate price and offer eligibility at checkout. Explain price changes to the customer rather than trusting client totals.
- Cache invalidation must occur when prices/offers change.

## Acceptance checks
- Boundary dates, expired offers, invalid discounts and rounding are tested.
- Tampered client totals are ignored.
- Historical orders retain their recorded prices after catalog updates.

## Verified Implementation Pattern
- **Time-Bounded Offer Validation**: `Product.is_offer_active(now=None)` checks `offer=True` and validates `offer_start_date <= now <= offer_end_date`.
- **Authoritative Effective Price**: `Product.effective_price` dynamically serves `offered_price` during valid windows and cleanly falls back to standard `price` once expired.
- **Checkout Snapshot Integrity**: `OrderService.submit_order_from_card` verifies each item's current `effective_price` before freezing the immutable unit price snapshot into `OrderItem`. Stale or tampered client totals are never accepted.
