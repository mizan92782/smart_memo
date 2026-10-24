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
