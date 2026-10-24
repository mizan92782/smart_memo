---
name: purchase-supplier-management
description: Supplier directory, purchase documents, receiving, purchase costs and stock entry.
---
# Purchase and Supplier Management

## Rules
- Supplier and purchase records are tenant/store scoped.
- Separate purchase draft, submitted/approved purchase, partially received purchase if supported, and fully received purchase.
- A purchase order is not inventory receipt. Increase stock only when goods are confirmed received.
- Store quantity, unit, unit cost, line total, charges, supplier, date, reference and status.
- Use decimal-safe money and quantity calculations.
- Record stock movements linked to purchase receipt lines.
- Define handling of partial receipt, damaged goods, supplier returns and corrections.
- Keep purchase costs private from customers and unauthorized staff.
- Avoid destructive edits to completed purchase records; use correction/reversal records where appropriate.

## Acceptance checks
- Draft purchase does not affect on-hand stock.
- Receiving goods updates inventory atomically and exactly once.
- Duplicate receipt requests cannot double-count stock.
- Purchase history and stock ledger can be reconciled.

## Verified Architecture Patterns
- Store suppliers in store-scoped `Supplier` model with `UniqueConstraint(fields=['store', 'name'])`.
- PO lifecycle state machine: `DRAFT -> SUBMITTED -> RECEIVED` (or `CANCELLED`).
- Stock receiving routes via `InventoryService.receive_stock(store, product, qty, reference_id, actor, notes)` inside a database transaction with `select_for_update()`.
- Customer access strictly blocked with `IsVendor` permission (403 Forbidden).
- Cross-vendor IDOR prevented by filtering `store__vendor=request.user` returning 404 for unowned purchase IDs.
