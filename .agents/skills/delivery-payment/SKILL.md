---
name: delivery-payment
description: Pickup, home delivery, delivery fees, cash-on-delivery and payment state.
---
# Delivery and Payment

## Rules
- Support pickup and home delivery as distinct fulfillment methods.
- Snapshot the selected delivery address and relevant contact details on the order; changing a customer profile later must not rewrite an existing order.
- Validate that the store supports the chosen fulfillment method and delivery area.
- Keep order, fulfillment and payment statuses separate.
- COD means payment is expected at delivery; it does not mean payment is already collected.
- Record who confirmed collection and when, according to the operational model.
- Calculate delivery charges on the server and preserve the charged amount in the order snapshot.
- Do not store raw card details or secrets. Integrate payment providers only through approved flows.
- Define cancellation and refund behavior for each payment method.
- Use idempotent event handling for delivery and payment callbacks.

## Acceptance checks
- Unsupported fulfillment/payment options are rejected.
- Delivery completion alone does not falsely mark COD as collected.
- Fees and address snapshots remain historically accurate.

## Verified Implementation Pattern
- **Fulfillment Capability Guards**: Checkout verifies `store.pickup_enabled` or `store.delivery_enabled` and checks `subtotal >= store.min_order_amount` before accepting home delivery orders.
- **Snapshot Immutability**: Order permanently freezes `delivery_address`, `delivery_fee`, `customer_phone_snapshot`, and product pricing, guaranteeing historical accuracy even if customer profile changes.
- **Decoupled COD Lifecycle**: `Order.payment_status` remains `PENDING` during transit and fulfillment when `payment_collected=False`. Payment is explicitly confirmed via `POST /orders/{id}/collect-payment/`, stamping `paid_at` and `payment_collected_by` while syncing `SalesMemo.amount_paid`.

