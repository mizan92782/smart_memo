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

## Verified Implementation Pattern
- **Draft Memo Lifecycle & Endpoints**:
  - `GET /cards/active/`: retrieve or auto-initialize customer's current draft memo.
  - `POST /cards/{id}/add-item/`: add product to memo enforcing single-store rule and zero stock deduction.
  - `POST /cards/{id}/update-item/`: adjust item quantity with Decimal precision.
  - `POST /cards/{id}/remove-item/`: delete an item from memo; resets `card.store = None` if memo becomes empty.
  - `POST /cards/{id}/clear/`: empty draft memo and reset store binding.
- **Tenant Isolation & IDOR Protection**: `CardViewSet` requires `IsAuthenticated` and scopes `get_queryset()` strictly to `user=request.user`. Customer A cannot inspect, modify, or add items to Customer B's draft memo (404 / 403).
- **Authoritative Price Revalidation at Checkout**: `OrderService.submit_order_from_card` verifies each item against `Product.effective_price` and product active status before creating the order. If an offer expired or price was updated while sitting in draft, the authoritative price is updated automatically and line totals recalculated.
- **Multi-Store Concurrent Draft Memos & Store Entry**:
  - `GET /cards/active/?store_id=<id>`: retrieves or auto-initializes the active draft memo specifically bound to that store.
  - `POST /stores/{id}/memo/`: customer enters a specific store in the marketplace and gets an instant store-scoped draft memo.
  - Customers can maintain parallel, non-colliding draft memos across multiple stores simultaneously (e.g., Grocery store memo, Pharmacy memo).
- **In-Store Walk-In Shopping Mode (`walk_in`) & Counter Product Handover**:
  - Customers physically walking inside a store set `shopping_mode='walk_in'` and add items to their memo as they walk around the store.
  - At in-store checkout (`fulfillment_type='walk_in'`), delivery fees are suppressed (`0.00`) and no delivery address is required.
  - Store owners/staff collect the picked items, accept on-the-spot payment, and hand over products via `POST /orders/{id}/handover/`, immediately completing the order and issuing the finalized `SalesMemo`.
- **Database-Level User & Vendor Fields**:
  - `Card`, `Order`, and `SalesMemo` each have explicit, indexed database foreign keys for both customer/user (`user` / `customer`) and store vendor (`vendor`).
  - Database `.save()` and repository methods automatically synchronize `vendor` from `store.vendor` / `order.store.vendor`.
  - Seamless dual-perspective querying: customers query their own cards (`CardRepository.get_by_user`), vendors can query cards directed to their stores (`CardRepository.get_by_vendor`, `GET /cards/?as_vendor=true`), and both perspectives are serialized with `vendor_email` and `customer_email`.
- **Saved Store Memos & Future Visit Planning (`is_saved_for_later`)**:
  - Customers can create named planning memos specifically for future store visits (`is_saved_for_later=True`, `planned_visit_date`) without colliding with their active shopping cart.
  - `GET /cards/saved/?store_id=<id>`: retrieves saved planning lists scoped to a store.
  - `POST /cards/create-saved/`: directly creates a new named future planning memo.
  - `POST /cards/{id}/save-for-later/`: defers an active cart to saved status.
  - `POST /cards/{id}/activate/`: activates a saved memo as the active cart for that store; if an active cart with items already exists, automatically swaps it to saved status so no items are lost.
  - `POST /cards/{id}/duplicate/`: clones a memo and all item snapshots into an independent saved or active memo.
- **Digital Sales Memo Wallet, Thermal Receipts & Customer Spending Analytics**:
  - `GET /orders/sales-memos/`: centralized digital receipt wallet for customers across all visited stores; vendors can filter by store or query as vendor (`?as_vendor=true`).
  - `SalesMemo.format_thermal_receipt()`: formats receipts into 40-column monospace slips suitable for 58mm/80mm POS thermal printers; exposed via `thermal_receipt` field and `GET /orders/{id}/thermal-receipt/`.
  - `GET /orders/customer-spending/`: multi-store customer analytics calculating total spent, total saved, and store-by-store breakdown using pure SQL database aggregations (`Coalesce(Sum(...))`).
- **In-Store Shelf Barcode Scanning**:
  - `POST /cards/{id}/scan-add/`: enables in-store shoppers to scan physical barcodes or SKUs directly off shelves; auto-resolves product in the store, validates stock, and adds or increments line item.
- **In-Store Basket Picking Checklist & Aisle Route Sequencing**:
  - `CardItem` tracks `is_picked` and `picked_at` timestamps as customers gather items into handheld baskets.
  - `POST /cards/{id}/toggle-item-picked/`: toggles individual item picked status and returns real-time progress metrics (`total_items_count`, `picked_items_count`, `is_fully_picked`, `picking_progress_percent`).
  - `POST /cards/{id}/batch-pick/`: updates multiple items in a single atomic operation.
  - `GET /cards/{id}/?sort_by=aisle` / `GET /cards/active/?store_id=<id>&sort_by=aisle`: sequences products by physical store layout (`product__aisle`, `product__shelf_location`) for non-backtracking walk-through routes.

