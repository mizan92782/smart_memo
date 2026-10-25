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

## Verified Implementation Patterns
- **Physical Inventory Reconciliation Sessions**: `StockReconciliation` snapshots `balance.on_hand` for counted products, calculates individual discrepancies and net financial variance value.
- **Reservation Guard During Reconciliation**: Applying batch reconciliation acquires row locks (`select_for_update`) and strictly validates `new_on_hand >= balance.reserved`, guaranteeing ongoing active customer orders cannot be oversold due to physical count write-offs.
- **Traceable Ledger & Audit Synchronization**: Count variances generate `StockMovementType.RECONCILIATION` entries in `StockLedgerEntry` stamped with the reconciliation session ID, write an immutable `AuditLog` entry, and invalidate tenant catalog caches in O(1) time.
- **Inter-Store Stock Transfers & Transit Ledger**: Multi-store stock movements operate via `StockTransfer` with strict state machine (`DRAFT -> IN_TRANSIT -> RECEIVED / CANCELLED`). Dispatches deduct from origin with `StockMovementType.TRANSFER_OUT`; arrivals credit destination with `TRANSFER_IN` (auto-provisioning product matching Barcode/SKU/Name); cancellations restore stock with `TRANSFER_CANCEL_RESTORE`. Driver waybills format printable 40-col monospace thermal slips.
- **Perishable Batch Tracking & FEFO Allocation**: Perishable goods track `ProductBatch` with manufacture/expiry dates and clearance discounts. Stock allocation uses First-Expired, First-Out (`FEFO`) ordering with row-locks. Spoilage disposal atomically decrements batch quantity, decreases store on-hand stock protecting customer reservations (`new_on_hand >= reserved`), records `StockMovementType.BATCH_DISPOSAL`, logs `AuditAction.BATCH_DISPOSED`, and scans near-expiry thresholds triggering `NotificationType.BATCH_EXPIRY_ALERT`.
