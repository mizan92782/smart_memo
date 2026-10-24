---
name: memo-management
description: Customer shopping drafts, memo items, totals, and transition from draft to order.
---
# Memo Management

## Definitions
A draft memo is an editable shopping list. A submitted order is a customer's request to purchase. A finalized sales memo/receipt documents a completed sale. These concepts must not be conflated.

## Rules
- Decide whether a memo belongs to one store; recommended default: one store per memo/order.
- A memo item records product reference, quantity, measurement unit and display/snapshot data appropriate to its lifecycle.
- Validate that products belong to the selected store and are orderable.
- Recalculate subtotal, offers, fees and total on the server.
- Draft edits do not create sales or deduct stock.
- At submission, revalidate store status, price, offers, quantity and stock policy.
- Define whether draft items persist across devices and whether stale drafts expire.
- Protect memo ownership; customers can modify only their own drafts.
- Use idempotency controls for submission to prevent duplicate orders on retry.

## Acceptance checks
- Customers cannot add products from an unauthorized or different store when single-store memos are used.
- Draft creation does not create a sale or stock movement.
- Invalid quantities and unavailable products are handled clearly.
- Retried submissions do not create duplicate orders.
