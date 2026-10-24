---
name: inventory-management
description: Stock ledger, current stock, reservations, adjustments, low-stock alerts and concurrency.
---
# Inventory Management

## Core model
Prefer an auditable stock-movement ledger plus a current-balance representation optimized for reads. Define which representation is authoritative and how reconciliation works.

## Rules
- Scope inventory by store and product.
- Use appropriate decimal precision for weight/volume and enforce valid quantity increments.
- Record every movement with type, quantity, timestamp, actor, store/product and source reference.
- Distinguish on-hand, reserved and available quantities when reservation is enabled.
- `available = on_hand - reserved` is a common rule; adapt only with documented business logic.
- Prevent overselling with transactions plus row locks, conditional updates, or equivalent database-safe concurrency control.
- Do not modify stock by silently overwriting a quantity without recording an adjustment movement.
- Never deduct stock for a draft memo.
- Define when stock is reserved, converted to sold stock, restored after cancellation, and adjusted for returns/damage.
- Make repeated processing idempotent; the same order event must not create duplicate movements.
- Trigger low-stock alerts from configured thresholds without blocking the primary transaction.

## Acceptance checks
- Concurrent orders cannot oversell stock.
- Each stock change has a traceable movement reference.
- Failed order/purchase operations roll back related stock changes.
- Reconciliation can detect balance/ledger mismatches.
