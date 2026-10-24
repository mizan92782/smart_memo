---
name: order-management
description: Order lifecycle, status transitions, acceptance, cancellation and fulfillment consistency.
---
# Order Management

## Rules
- Define a finite order state machine, for example: submitted -> accepted -> preparing -> ready_for_pickup / out_for_delivery -> completed. Rejected/cancelled transitions must be explicitly defined.
- Do not allow arbitrary status updates from clients; each transition requires an authorized actor and valid current state.
- Keep order status, fulfillment status and payment status distinct.
- Use database transactions for order creation, order items, inventory reservations and required audit events.
- Protect against duplicate requests with idempotency keys or equivalent deduplication.
- Decide when the vendor may reject/cancel and how customers are informed.
- Define partial fulfillment, substitutions, refunds and returns as explicit capabilities rather than implicit side effects.
- Record timestamps and actor for important status transitions.
- Keep historical item price/discount snapshots stable.

## Acceptance checks
- Invalid state transitions are rejected.
- Concurrent acceptance/cancellation does not double-reserve or double-release stock.
- Duplicate submission and event processing are idempotent.
- Every important transition is auditable.
