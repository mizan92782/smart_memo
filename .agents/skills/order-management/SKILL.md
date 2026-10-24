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

## Verified Implementation Pattern
- **Finite State Machine**: Strict 5-step pipeline: `SUBMITTED` -> `ACCEPTED` (`POST /orders/{id}/accept/`) -> `PREPARING` (`POST /orders/{id}/prepare/`) -> `READY_FOR_PICKUP` or `OUT_FOR_DELIVERY` (`POST /orders/{id}/dispatch/`) -> `COMPLETED` (`POST /orders/{id}/fulfill/`).
- **Audit Timestamps**: Every step permanently records transition timestamps: `accepted_at`, `preparing_at`, `dispatched_at`, `completed_at`, `cancelled_at`, and `paid_at`.
- **Actor Cancellation Boundaries**: Customers can cancel only when the order is `SUBMITTED` or `ACCEPTED` before preparation begins. Once in `PREPARING`, customer cancellation is rejected (400 Bad Request) to protect vendor prep investment. Vendors retain authority to reject/cancel at any pre-completion stage, atomically releasing reserved stock via `InventoryService.release_reserved_stock`.
- **Framework Action Naming**: Action method is named `dispatch_order` with `url_path='dispatch'` to avoid overriding Django's core `View.dispatch` method.
- **Automated Lifecycle Notifications**: Customer receives real-time in-app notifications for `ORDER_ACCEPTED`, `ORDER_PREPARING`, `ORDER_READY_FOR_PICKUP`, `ORDER_OUT_FOR_DELIVERY`, `ORDER_COMPLETED`, and `ORDER_CANCELLED`.
- **In-Store Walk-In & Counter POS**: Orders with `fulfillment_type='walk_in'` or `'pickup'` automatically generate a 6-digit numeric verification code (`walk_in_code`). Counter staff/vendors look up incoming walk-ins via `POST /orders/counter-lookup/` with strict vendor tenancy checks, verify items, and complete handover via `POST /orders/{id}/handover/`, copying `walk_in_code_snapshot` into the immutable `SalesMemo`.
