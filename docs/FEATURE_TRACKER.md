# Smart Memo System — Feature & Development Tracker

This document is the living single source of truth for feature development status, verified test suites, technical debt, and progress tracking across the Smart Memo System SaaS.

---

## 📌 Last Working Feature
- **Feature Name**: Full Multi-Tenant SaaS Platform (Customer Order Item Returns, Restocking & Refund Credit Notes, Production CI/CD Pipeline & Database Backup/Restore Automation, Saved 'Buy Next Time' Store Memos & Multi-Memo Planning, Database-Level User & Vendor Fields on Cards & Memos, Multi-Store Memo Cards & In-Store Walk-In Shopping, Delivery Driver Assignment & Real-Time Dispatch Tracking, Store Promotional Coupons & Order Discounts, Verified Customer Store Reviews & Ratings, Physical Inventory Audit & Batch Stock Reconciliation, Customer Saved Delivery Addresses & Dynamic Distance-Based Delivery Fees, Production Rate Limiting & Abuse Controls, Audit Logging & Activity Trail, Platform Administration & Store Governance, Authentication Lifecycle & User Profile Management, Order Fulfillment Pipeline, Draft Memo Management & Isolation, Deployment Observability, Tenant-Safe Caching, Delivery & Payment Decoupling, Notifications & Alerting Engine, Discovery & Favorites, Draft Memo Checkout, Reports, Purchases, Orders, Inventory, Cards, Products, Categories, Stores & Users)
- **Status**: 🟢 **Completed & Verified (256 Tests Passing)**
- **Last Verified Working**: 2026-10-25
- **Current State**:
  - `orders` (Customer Order Item Returns, Restocking & Refund Credit Notes): Complete return lifecycle for completed orders (`OrderReturn`, `OrderReturnItem`). Customers can submit item return requests with reasons (`POST /orders/returns/request/`), store vendors review and approve/reject (`POST /orders/returns/{id}/process/`), with automatic pessimistic row-locked stock replenishment (`StockBalance.on_hand`) and audit logging (`StockMovementType.RETURN`), damage/waste disposal logging (`StockMovementType.DAMAGE_LOSS`), proportional coupon discount deduction and loyalty point/stamp reversals, full order refund status synchronization (`PaymentStatus.REFUNDED`), and 40-column monospace thermal credit note slip rendering (`GET /orders/returns/{id}/credit-note/?receipt_format=text`). Passing 8/8 tests.
  - `devops` (Production CI/CD Pipeline & Automated Health/Backup Scripts): GitHub Actions workflow (`.github/workflows/ci.yml`) automating Ruff linting, Bandit security scanning, migration dry-runs, and full test suite execution with PostgreSQL 15 and Redis 7 service containers. Automated production PostgreSQL database backup script (`scripts/backup_db.sh`) with gzip compression, SHA256 integrity checksums, 30-day pruning, and safe restoration script (`scripts/restore_db.sh`).

  - `cards` (Saved Store Memos & Multi-Memo Planning): Dedicated "buy next time" planning memos per store (`is_saved_for_later=True`, `planned_visit_date`). Customers can create named future visit lists (`POST /cards/create-saved/`), defer active carts (`POST /cards/{id}/save-for-later/`), activate a saved memo (`POST /cards/{id}/activate/`) with automatic safe swap of existing non-empty carts (zero item loss), duplicate past or saved memos with all items (`POST /cards/{id}/duplicate/`), and inspect store-scoped saved lists (`GET /cards/saved/?store_id=<id>`). Passing 7/7 tests.
  - `cards` & `orders` (Database-Level User & Vendor Fields): Explicit relational foreign keys (`user`/`customer` and `vendor`) at the database level on `Card`, `Order`, and `SalesMemo`. Automatic database synchronization in `.save()` and repositories, bidirectional query capabilities (`CardRepository.get_by_vendor`, `OrderRepository.get_by_vendor`), API vendor filtering (`GET /cards/?as_vendor=true`), bounded N+1 query elimination using `Prefetch` with `select_related('customer', 'vendor')`, and full serializer exposure. Passing 6/6 tests.
  - `cards` & `orders` (Multi-Store Memo Cards & In-Store Walk-In Shopping): Support for multi-vendor digital marketplace model. Customers can enter distinct stores (`POST /stores/{id}/memo/`), maintaining concurrent, non-colliding draft memos across multiple stores (`GET /cards/active/?store_id=<id>`). In-store walk-in shopping mode (`shopping_mode='walk_in'`) allows customers to add items while physically walking in the store, checkout with zero delivery fee and no address required (`fulfillment_type='walk_in'`), and have store owners collect items and execute instant on-the-spot handover (`POST /orders/{id}/handover/`) with cash collection and immediate SalesMemo issuance. Passing 9/9 tests.
  - `orders` (Delivery Driver Assignment & Real-Time Dispatch Tracking): Real-time delivery personnel assignment (`delivery_person_name`, `delivery_person_phone`, `delivery_vehicle_type`, `delivery_tracking_notes`, `estimated_delivery_time`, `auto_dispatch`) via `POST /orders/{id}/assign-delivery/`. Reassignment support while in transit, pickup order and terminal order rejection, customer driver visibility on order retrieval, automated dispatching to `OUT_FOR_DELIVERY` with `dispatched_at` stamped, instant customer notification with driver contact details, and strict server-side tenant isolation / IDOR prevention. Passing 9/9 tests.
  - `stores` (Store Promotional Coupons & Order Discounts): `Coupon` and `CouponUsage` models, supporting percentage discounts with maximum ceiling caps (`max_discount_amount`) and fixed currency amounts, `min_order_amount`, `max_uses`, `max_uses_per_customer`, and active time windows (`start_date`, `end_date`). Draft memo coupon application (`POST /cards/{id}/apply-coupon/`) with live discount and estimated total preview, coupon detachment (`POST /cards/{id}/remove-coupon/`), authoritative checkout revalidation and discount deduction in `OrderService.submit_order_from_card`, immutable snapshots on `Order` and `SalesMemo`, atomic usage ledger tracking (`CouponUsage`), and vendor coupon management API (`/stores/{id}/coupons/`, `/stores/coupons/{id}/`). Passing 10/10 tests.
  - `stores` (Verified Customer Store Reviews & Ratings): `StoreReview` model with completed order verification (`unique_together = ('store', 'customer')`), automated calculation and denormalization of `average_rating` and `total_reviews` on `Store` via SQL aggregation, customer review submission (`POST /stores/{id}/reviews/`), public review listing (`GET /stores/{id}/reviews/`), vendor official reply (`POST /stores/reviews/{id}/reply/`), review deletion by customer or staff (`DELETE /stores/reviews/{id}/`), cache invalidation on rating updates, and tenant-level authorization. Passing 10/10 tests.
  - `inventory` (Physical Inventory Audit & Batch Stock Reconciliation): `StockReconciliation` and `StockReconciliationItem` models, draft count session snapshotting system on-hand balances, discrepancy computation (`physical_stock - system_stock`) and monetary variance valuation, atomic batch application (`POST /inventory/reconciliations/{id}/apply/`) updating `StockBalance` with row locking (`select_for_update`), enforcing active order reservation invariants, posting `StockMovementType.RECONCILIATION` entries to the immutable `StockLedgerEntry` ledger, recording `AuditAction.INVENTORY_RECONCILED` audit logs, invalidating cache, and enforcing strict vendor tenant isolation. Passing 8/8 tests.
  - `users` (Customer Saved Delivery Addresses & Dynamic Fees): `CustomerAddress` model with soft deletion, automated single default address invariant (`is_default`), coordinate validation, strict customer tenant isolation / IDOR prevention, dynamic tiered Haversine delivery fee calculator (`POST /stores/{id}/calculate-delivery-fee/`), memo checkout address integration snapshotting recipient, address, phone and instructions to `Order`, charging dynamic distance-based fees. Passing 10/10 tests.
  - `shared/throtling` & `users` (Production Rate Limiting & Abuse Controls): Scoped rate throttles (`LoginAnonThrottle` 5/min, `LoginUserThrottle` 5/min, `SignupAnonThrottle` 5/min, `NearbyDiscoveryThrottle` 30/min), global rate configuration in `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`, custom exception handler with automated `available_in_seconds` retry-after delay payload and HTTP 429 status response. Passing 3/3 tests.
  - `audit` (Audit Logging & Activity Trail): Immutable append-only audit ledger (`AuditLog`) recording all critical state mutations (store verification/suspension/reactivation, inventory adjustments, order cancellations, COD payment collections, password changes) with actor snapshot, IP address, user-agent, and structured JSON diffs. Enforces model-level immutability (`.save()` updates and `.delete()` blocked), `ReadOnlyModelViewSet` (POST/PUT/DELETE blocked with 405), and strict tenant isolation (vendors limited to their stores, staff/admin see platform-wide, customers blocked). Passing 13/13 tests.
  - `stores` (Platform Administration & Governance): Administrative store verification (`is_verified`, `verified_at`, `verification_notes`), store suspension (`POST /stores/{id}/suspend/`), reactivation (`POST /stores/{id}/activate/`), platform-wide metrics overview (`GET /stores/governance-overview/`), exclusion of unverified/inactive stores from public discovery and checkout orders, role governance enforced with `IsStaffOrAdmin`. Passing 16/16 tests.
  - `users` (Authentication Lifecycle & Profile Management): DRF Token authentication (`rest_framework.authtoken`), login (`POST /users/login/`) delivering tokens and user roles, logout (`POST /users/logout/`) revoking tokens and sessions, password changes (`POST /users/change-password/`) verifying current hash, rotating tokens, and profile retrieval and updates (`GET / PATCH /users/profile/`) strictly isolated per actor. Passing 27/27 tests.
  - `orders` (Fulfillment Pipeline): Complete 5-stage order fulfillment state machine (`SUBMITTED -> ACCEPTED -> PREPARING -> READY_FOR_PICKUP / OUT_FOR_DELIVERY -> COMPLETED`) with transition timestamps (`accepted_at`, `preparing_at`, `dispatched_at`, `completed_at`), actor-based cancellation policy (customers blocked from cancelling once prep has started), automated customer lifecycle alerts, and clean non-colliding action routing. Passing 9/9 tests.
  - `cards` (Draft Memo Management): Customer draft shopping memos with active memo resolution (`GET /cards/active/`), single-store scoping, zero premature stock impact, full item operations (`add_item`, `update_item`, `remove_item`, `clear`), store unbinding on empty memo, strict customer tenant isolation, and authoritative dynamic catalog price/offer revalidation at checkout. Passing 12/12 tests.
  - `observability`: Container liveness (`/health/live/`), deep readiness probe (`/health/ready/`) validating PostgreSQL connectivity, pending migrations via `MigrationExecutor`, and cache accessibility without leaking secrets. Content negotiation on `/health/` supporting JSON metrics. Passing 6/6 tests.
  - `caching`: `CacheService` with O(1) versioned tenant namespaces (`version:{namespace}:store:{store_id}`). Catalog and store public details cached with automatic invalidation on store updates, category CRUD, and product changes. Authoritative checkout bypasses cache. Passing 4/4 tests.
  - `orders` (Delivery & Payment): Decoupled Cash On Delivery (COD) payment collection (`POST /orders/{id}/collect-payment/`), customer phone snapshotting, fulfillment validation (`pickup_enabled`, `delivery_enabled`, `min_order_amount`). Passing 4/4 tests.
  - `notifications`: In-app & Celery async alerting engine (`Notification`), idempotent dispatching, automated order lifecycle notifications (`ORDER_SUBMITTED`, `ORDER_ACCEPTED`, `ORDER_PREPARING`, `ORDER_READY_FOR_PICKUP`, `ORDER_OUT_FOR_DELIVERY`, `ORDER_COMPLETED`, `ORDER_CANCELLED`), real-time low-stock alerts triggered on inventory drops, unread count badge endpoints, and recipient-level isolation. Passing 8/8 tests.
  - `stores`: Multi-tenant anchor model with slug generation, vendor scoping, public discovery endpoints, geospatial Haversine nearby discovery (`/stores/nearby/`) with coordinate validation, bounding-box pre-filtering, distance calculation, non-location fallback, and customer favorite stores (`FavoriteStore`) with unique constraints and tenant isolation, passing tests.
  - `users`: Custom User model with roles (`CUSTOMER`, `VENDOR`, `STAFF`, `SUPERUSER`), email identity, registration, profile retrieval, passing tests.
  - `categories`: Store-scoped category hierarchy with unique constraints per store, passing tests.
  - `products`: Store-scoped catalog with SKU, Decimal pricing, time-bounded offers (`is_offer_active`), dynamic `effective_price`, and public search, passing tests.
  - `inventory`: Concurrency-safe `StockBalance` with check constraints and `StockLedgerEntry` append-only audit trail using row-level locking (`select_for_update`), passing tests.
  - `purchases`: Store-scoped `Supplier` directory, `Purchase` and `PurchaseItem` models, draft PO workflow with zero premature stock deduction, atomic receipt into inventory via `InventoryService.receive_stock` with audit ledger logging, duplicate receipt rejection, passing tests.
  - `reports`: Vendor analytics engine aggregating gross sales, net product revenue, delivery fee totals, COD collected vs outstanding, inventory low-stock alerts, and procurement costs with store-level tenant authorization, passing tests.

---

## 🚦 Feature Roadmap & Execution Status

| Phase | Feature Module | Target Scope | Implementation Status | Automated Tests | Security Tests | Tenant Isolated |
|---|---|---|:---:|:---:|:---:|:---:|
| **1** | **Identity & Tenant Foundation** | Custom User (`email`), Roles (`CUSTOMER`, `VENDOR`, `STAFF`), Store Model, Tenant Permissions | 🟢 Completed | 🟢 5 Passing | 🟢 5 Passing | 🟢 Enforced |
| **2** | **Store Management** | Store profile, coordinates, opening hours, delivery settings, vendor association, public discovery | 🟢 Completed | 🟢 8 Passing | 🟢 8 Passing | 🟢 Enforced |
| **3** | **Tenant Catalog & Pricing** | Store-scoped `Category` and `Product`, `MeasurementUnit`, `CurrencyUnit`, Decimal pricing, SKU, Offers | 🟢 Completed | 🟢 9 Passing | 🟢 9 Passing | 🟢 Enforced |
| **4** | **Inventory Ledger & Concurrency** | `StockBalance` with row locking, `StockLedgerEntry` audit trail, reservation/fulfillment/adjustment | 🟢 Completed | 🟢 6 Passing | 🟢 6 Passing | 🟢 Enforced |
| **5** | **Customer Discovery & Memos** | Catalog browse, single-store Draft Shopping Memos (`cards`), stock non-deduction, checkout endpoint | 🟢 Completed | 🟢 7 Passing | 🟢 4 Passing | 🟢 Enforced |
| **6** | **Order Lifecycle & Reservations** | Finite state machine, atomic stock reservations, cancellation rollback, idempotency, Sales Memo | 🟢 Completed | 🟢 7 Passing | 🟢 7 Passing | 🟢 Enforced |
| **7** | **Suppliers & Purchase Receiving** | Supplier directory and direct purchase receiving into inventory ledger with audit trail | 🟢 Completed | 🟢 4 Passing | 🟢 4 Passing | 🟢 Enforced |
| **8** | **Reports & Analytics** | Low stock alerts, sales analytics, query optimization (N+1), rate-limiting, monitoring | 🟢 Completed | 🟢 5 Passing | 🟢 3 Passing | 🟢 Enforced |
| **9** | **Nearby Discovery & Favorites** | Geospatial Haversine store search, distance ranking, radius filtering, fallback, customer favorite stores | 🟢 Completed | 🟢 17 Passing | 🟢 8 Passing | 🟢 Enforced |
| **10** | **Notifications & Alerting Engine** | Order lifecycle notifications, automated low-stock vendor alerts, async Celery dispatch, unread feed | 🟢 Completed | 🟢 8 Passing | 🟢 3 Passing | 🟢 Enforced |
| **11** | **Delivery & Payment Decoupling** | Min order validation, delivery/pickup capability enforcement, decoupled COD payment collection | 🟢 Completed | 🟢 4 Passing | 🟢 4 Passing | 🟢 Enforced |
| **12** | **Tenant-Safe Caching** | O(1) versioned tenant namespaces, catalog & store caching, write-invalidation, zero-leakage keys | 🟢 Completed | 🟢 4 Passing | 🟢 4 Passing | 🟢 Enforced |
| **13** | **Deployment Observability** | Container liveness `/health/live/`, deep readiness probe `/health/ready/`, migration check, secret safety | 🟢 Completed | 🟢 6 Passing | 🟢 6 Passing | 🟢 Enforced |
| **14** | **Order Fulfillment Pipeline** | Full 5-stage lifecycle state machine (`SUBMITTED -> ACCEPTED -> PREPARING -> READY/DISPATCHED -> COMPLETED`), audit timestamps, customer cancellation guards | 🟢 Completed | 🟢 5 Passing | 🟢 5 Passing | 🟢 Enforced |
| **15** | **Draft Memo Management & Isolation** | Memo item CRUD (`active`, `add_item`, `update_item`, `remove_item`, `clear`), empty store reset, catalog price revalidation at checkout | 🟢 Completed | 🟢 5 Passing | 🟢 5 Passing | 🟢 Enforced |
| **16** | **Authentication Lifecycle & Profiles** | DRF Token auth, `login`, `logout`, `change-password` with token rotation, isolated `profile` GET/PATCH | 🟢 Completed | 🟢 13 Passing | 🟢 8 Passing | 🟢 Enforced |
| **17** | **Platform Admin & Store Governance** | Store verification (`verify`, `suspend`, `activate`), unverified checkout/discovery guard, platform overview metrics | 🟢 Completed | 🟢 12 Passing | 🟢 12 Passing | 🟢 Enforced |
| **18** | **Audit Logging & Activity Trail** | Immutable append-only audit trail (`AuditLog`), automated logging on store governance, inventory adjustments, orders & security events, tenant-scoped read-only API | 🟢 Completed | 🟢 13 Passing | 🟢 13 Passing | 🟢 Enforced |
| **19** | **Rate Limiting & Abuse Controls** | Scoped throttling (`LoginAnonThrottle`, `LoginUserThrottle`, `SignupAnonThrottle`, `NearbyDiscoveryThrottle`), retry delay metadata in exception handler, 429 response structure | 🟢 Completed | 🟢 3 Passing | 🟢 3 Passing | 🟢 Enforced |
| **20** | **Customer Addresses & Dynamic Delivery Fees** | Saved addresses (`CustomerAddress`), single default enforcement, soft-deletion, IDOR protection, Haversine delivery fee quote, checkout snapshotting | 🟢 Completed | 🟢 10 Passing | 🟢 10 Passing | 🟢 Enforced |
| **21** | **Physical Inventory Audit & Batch Reconciliation** | Physical inventory stock takes (`StockReconciliation`), variance calculation, atomic ledger reconciliation, reservation guard | 🟢 Completed | 🟢 8 Passing | 🟢 8 Passing | 🟢 Enforced |
| **22** | **Verified Customer Store Reviews & Ratings** | Completed order verified reviews (`StoreReview`), anti-spam unique guard, denormalized O(1) store average rating, vendor replies, moderation | 🟢 Completed | 🟢 10 Passing | 🟢 10 Passing | 🟢 Enforced |
| **23** | **Store Promotional Coupons & Order Discounts** | Store-scoped discount coupons (`Coupon`), percentage/fixed discounts, min order amounts, usage limits, draft memo application, authoritative checkout calculation, usage ledger (`CouponUsage`) | 🟢 Completed | 🟢 10 Passing | 🟢 10 Passing | 🟢 Enforced |
| **24** | **Delivery Driver Assignment & Real-Time Tracking** | Vendor driver assignment (`name`, `phone`, `vehicle_type`, `tracking_notes`, `estimated_delivery_time`), auto-dispatch, in-transit reassignment, pickup/terminal guards, customer notifications | 🟢 Completed | 🟢 9 Passing | 🟢 9 Passing | 🟢 Enforced |
| **25** | **Multi-Store Memos & In-Store Walk-In Shopping** | Marketplace parallel store draft memos, store-scoped active cards, in-store walk-in shopping mode, zero-fee walk-in checkout, vendor counter product handover & instant completion | 🟢 Completed | 🟢 9 Passing | 🟢 9 Passing | 🟢 Enforced |
| **26** | **Database-Level User & Vendor Fields** | Direct database-level foreign keys (`user`/`customer` and `vendor`) across `Card`, `Order`, `SalesMemo`, auto-population from store/order, dual-perspective queries (`CardRepository.get_by_vendor`, `OrderRepository.get_by_vendor`), `as_vendor=true` API filter, serializer exposure | 🟢 Completed | 🟢 6 Passing | 🟢 6 Passing | 🟢 Enforced |
| **27** | **Saved Store Memos & Multi-Memo Planning** | "Buy Next Time" planning memos (`is_saved_for_later`, `planned_visit_date`), memo deferral (`save-for-later`), activation with safe active memo swap (`activate`), cloning (`duplicate`), store-scoped saved listing (`GET /cards/saved/`) | 🟢 Completed | 🟢 7 Passing | 🟢 7 Passing | 🟢 Enforced |
| **28** | **In-Store Counter POS & 6-Digit Walk-In Code** | Counter POS lookup (`POST /orders/counter-lookup/`), walk-in 6-digit numeric verification code, instant handover, immutable SalesMemo snapshot | 🟢 Completed | 🟢 7 Passing | 🟢 7 Passing | 🟢 Enforced |
| **29** | **Digital Sales Memos, Receipts & Analytics** | Digital sales memo wallet (`GET /orders/sales-memos/`), thermal receipt 40-col formatting (`GET /orders/{id}/thermal-receipt/`), customer multi-store spending analytics (`GET /orders/customer-spending/`) | 🟢 Completed | 🟢 7 Passing | 🟢 7 Passing | 🟢 Enforced |
| **30** | **In-Store Shelf Barcode Scanning & QR Code** | Product barcode/SKU shelf scanner (`POST /cards/{id}/scan-add/`), public barcode lookup (`GET /products/api/barcode-lookup/`), standalone vector SVG QR codes (`GET /orders/{id}/qr-code/`), quick 1-tap reordering (`POST /orders/{id}/reorder/`) | 🟢 Completed | 🟢 7 Passing | 🟢 7 Passing | 🟢 Enforced |
| **31** | **In-Store Shelf Navigation & Basket Picking** | Aisle and shelf location tracking on products (`aisle`, `shelf_location`), basket picking checklist (`is_picked`, `picked_at`), progress metrics, toggle (`POST /cards/{id}/toggle-item-picked/`), batch pick (`POST /cards/{id}/batch-pick/`), walking aisle route sorting (`sort_by=aisle`) | 🟢 Completed | 🟢 6 Passing | 🟢 6 Passing | 🟢 Enforced |
| **32** | **Cross-Store Memo Comparison & Store Transfer** | Memo budget limits (`budget_limit`, `budget_remaining`, `is_over_budget`, `budget_used_percent`, `PATCH /cards/{id}/set-budget/`), cross-store catalog comparison (`POST /cards/{id}/compare-store/`) with barcode->SKU->name matching, price difference and savings calculation, store memo transfer (`POST /cards/{id}/transfer-store/`) with coupon decoupling | 🟢 Completed | 🟢 5 Passing | 🟢 5 Passing | 🟢 Enforced |
| **33** | **Store Loyalty Points & Visit Stamp Cards** | Store-scoped loyalty programs (`StoreLoyaltyProgram`, `POINTS` vs `STAMPS`), customer punch cards (`CustomerStoreLoyalty`), append-only ledger (`LoyaltyTransaction`), draft memo point/stamp redemption (`POST /cards/{id}/redeem-loyalty/`), checkout deduction & cancellation refund, order completion automated point/stamp award & thermal receipt snapshot | 🟢 Completed | 🟢 6 Passing | 🟢 6 Passing | 🟢 Enforced |
| **34** | **Customer Order Returns & Credit Notes** | Item returns on completed orders (`OrderReturn`, `OrderReturnItem`), customer submission (`POST /orders/returns/request/`), vendor review/approval (`POST /orders/returns/{id}/process/`), atomic inventory restock ledger, damage write-off, proportional discount/loyalty reversal, printable 40-col monospace credit note slip (`GET /orders/returns/{id}/credit-note/?receipt_format=text`) | 🟢 Completed | 🟢 8 Passing | 🟢 8 Passing | 🟢 Enforced |
| **35** | **Production CI/CD & Database DevOps** | GitHub Actions pipeline (`.github/workflows/ci.yml`) running lint, security, migration checks, and full automated test suite with Postgres/Redis services; production DB backup script with SHA256 checksums (`scripts/backup_db.sh`) and restore script (`scripts/restore_db.sh`) | 🟢 Completed | 🟢 Verified | 🟢 Verified | 🟢 Enforced |

*Total Active Automated Tests Passing: 256 / 256 (100% Passing)*


---

## 🧪 Automated Test Suite Tracker

| App / Domain | Test Suite File | Coverage Scope | Status | Last Run Result |
|---|---|---|:---:|:---:|
| **Users** | `users/tests/test_auth.py` | User creation, role assignment, registration, profile retrieval | 🟢 Passing | 5 / 5 OK |
| **Users** | `users/tests/test_user_lifecycle.py` | Login, logout, change-password with token rotation, profile isolation | 🟢 Passing | 13 / 13 OK |
| **Users** | `users/tests/test_delivery_addresses.py` | Saved addresses, default invariant, soft delete, IDOR, dynamic delivery fee & checkout snapshot | 🟢 Passing | 10 / 10 OK |
| **Users** | `users/tests/test_observability.py` | Liveness `/health/live/`, readiness `/health/ready/`, DB/cache/migration checks, secret safety | 🟢 Passing | 6 / 6 OK |
| **Stores** | `stores/tests/test_stores.py` | Slug generation, store updates, soft deletion | 🟢 Passing | 4 / 4 OK |
| **Stores** | `stores/tests/test_security.py` | Cross-tenant isolation, customer store creation block, public store discovery | 🟢 Passing | 4 / 4 OK |
| **Stores** | `stores/tests/test_nearby.py` | Haversine distance, radius filtering, coordinate validation, non-location fallback | 🟢 Passing | 6 / 6 OK |
| **Stores** | `stores/tests/test_favorites.py` | Idempotent favorites, customer isolation, unfavorite, unauthenticated block | 🟢 Passing | 4 / 4 OK |
| **Stores** | `stores/tests/test_caching.py` | O(1) versioned invalidation, isolated tenant keys, public detail caching, product write invalidation | 🟢 Passing | 4 / 4 OK |
| **Stores** | `stores/tests/test_platform_admin.py` | Store verification, suspension/reactivation, cross-tenant admin overview, unverified checkout guard | 🟢 Passing | 12 / 12 OK |
| **Stores** | `stores/tests/test_reviews.py` | Verified reviews, completed order checks, anti-spam unique guard, store average rating sync, replies | 🟢 Passing | 10 / 10 OK |
| **Stores** | `stores/tests/test_coupons.py` | Percentage coupons with cap, fixed amount, date validation, min order threshold, usage limits, checkout snapshotting | 🟢 Passing | 10 / 10 OK |
| **Stores** | `stores/tests/test_store_loyalty.py` | Store loyalty programs, customer punch cards, draft memo point/stamp redemption, checkout debit & cancellation refund, order completion award | 🟢 Passing | 6 / 6 OK |
| **Audit** | `audit/tests/test_audit_logging.py` | Immutable activity trail, model-level update/delete blocking, actor snapshotting, tenant isolation | 🟢 Passing | 13 / 13 OK |
| **Users** | `users/tests/test_throttling.py` | Login/signup/nearby rate limiting, Retry-After header, 429 response structure | 🟢 Passing | 3 / 3 OK |
| **Categories** | `categories/tests/test_categories.py` | Category creation, title capitalization, store association | 🟢 Passing | 1 / 1 OK |
| **Categories** | `categories/tests/test_security.py` | Cross-tenant category modification IDOR prevention | 🟢 Passing | 3 / 3 OK |
| **Products** | `products/tests/test_views.py` | Template listing and category product listing | 🟢 Passing | 2 / 2 OK |
| **Products** | `products/tests/test_security.py` | Cross-tenant product isolation, public catalog search | 🟢 Passing | 3 / 3 OK |
| **Inventory** | `inventory/tests/test_ledger.py` | Receiving, reserving, fulfilling, releasing stock & audit ledger | 🟢 Passing | 3 / 3 OK |
| **Inventory** | `inventory/tests/test_concurrency.py` | Row-locking, negative stock prevention, cross-tenant adjustment block | 🟢 Passing | 3 / 3 OK |
| **Inventory** | `inventory/tests/test_reconciliation.py` | Physical count sessions, variance calculation, atomic ledger reconciliation, reservation protection | 🟢 Passing | 8 / 8 OK |
| **Cards** | `cards/tests/test_cards.py` | Multi-product card, single-store enforcement, stock non-deduction | 🟢 Passing | 3 / 3 OK |
| **Cards** | `cards/tests/test_checkout.py` | Draft memo checkout to submitted order, inventory reservation, authorization | 🟢 Passing | 4 / 4 OK |
| **Cards** | `cards/tests/test_memo_management.py` | Draft memo item CRUD (`add`, `update`, `remove`, `clear`), empty reset, IDOR, offer revalidation | 🟢 Passing | 5 / 5 OK |
| **Cards** | `cards/tests/test_multi_store_memos.py` | Multi-store parallel cards, store entry action, walk-in shopping mode, zero-fee checkout, counter handover | 🟢 Passing | 9 / 9 OK |
| **Cards** | `cards/tests/test_database_level_fields.py` | Database-level user/customer and vendor fields on Card, Order, SalesMemo, auto-sync, vendor queries | 🟢 Passing | 6 / 6 OK |
| **Cards** | `cards/tests/test_saved_memos.py` | Saved "buy next time" planning memos, deferral, activation with safe swap, duplicate, IDOR | 🟢 Passing | 7 / 7 OK |
| **Products** | `products/tests/test_barcode_lookup.py` | Physical shelf barcode/SKU lookup, store catalog isolation | 🟢 Passing | 3 / 3 OK |
| **Cards** | `cards/tests/test_barcode_scan_add.py` | Scan shelf barcode directly into draft shopping memo, auto-increment, stock check | 🟢 Passing | 3 / 3 OK |
| **Orders** | `orders/tests/test_quick_reorder.py` | 1-tap quick reorder past order items into active shopping memo, catalog revalidation | 🟢 Passing | 1 / 1 OK |
| **Cards** | `cards/tests/test_aisle_picking.py` | In-store basket picking, progress indicators, batch pick, aisle walking route sequence | 🟢 Passing | 6 / 6 OK |
| **Cards** | `cards/tests/test_store_comparison_and_budget.py` | Cross-store comparison, price differences, memo store transfer, budget limits & over-budget alerts | 🟢 Passing | 5 / 5 OK |
| **Orders** | `orders/tests/test_state_machine.py` | Order submission, acceptance, fulfillment, cancellation, Sales Memo | 🟢 Passing | 4 / 4 OK |
| **Orders** | `orders/tests/test_idempotency.py` | Idempotency deduplication, cross-customer order isolation, cross-vendor isolation | 🟢 Passing | 3 / 3 OK |
| **Orders** | `orders/tests/test_performance.py` | N+1 query prevention on orders listing and catalog search (`assertNumQueries`) | 🟢 Passing | 2 / 2 OK |
| **Orders** | `orders/tests/test_delivery_payment.py` | Delivery/pickup store capability enforcement, min order validation, decoupled COD payment collection | 🟢 Passing | 4 / 4 OK |
| **Orders** | `orders/tests/test_fulfillment_pipeline.py` | Full 5-stage fulfillment pipeline (`prepare`, `dispatch`), timestamps, customer cancel guards | 🟢 Passing | 5 / 5 OK |
| **Orders** | `orders/tests/test_delivery_assignment.py` | Driver assignment, auto-dispatch, in-transit reassignment, pickup/terminal guards, notifications | 🟢 Passing | 9 / 9 OK |
| **Orders** | `orders/tests/test_counter_pos.py` | In-Store Counter POS, 6-digit walk-in code lookup, handover flow, cross-vendor isolation, sales memo snapshot | 🟢 Passing | 7 / 7 OK |
| **Orders** | `orders/tests/test_sales_memos_and_spending.py` | Digital sales memos wallet, thermal receipt 40-col formatting, store breakdown, customer spending analytics | 🟢 Passing | 7 / 7 OK |
| **Orders** | `orders/tests/test_order_returns.py` | Item return requests, vendor review, atomic stock restoration, damage logging, thermal credit notes | 🟢 Passing | 8 / 8 OK |
| **Purchases** | `purchases/tests/test_purchases.py` | Supplier creation, draft PO zero-stock impact, atomic receiving, duplicate rejection | 🟢 Passing | 4 / 4 OK |

| **Purchases** | `purchases/tests/test_security.py` | Cross-vendor PO IDOR block, customer PO access block, unauthenticated block | 🟢 Passing | 4 / 4 OK |
| **Reports** | `reports/tests/test_reports.py` | Database aggregations for sales, inventory low-stock alerts, procurement spending | 🟢 Passing | 3 / 3 OK |
| **Reports** | `reports/tests/test_security.py` | Cross-tenant store report IDOR protection, customer report block | 🟢 Passing | 3 / 3 OK |
| **Notifications** | `notifications/tests/test_notifications.py` | Event hooks, order alerts, low-stock threshold triggers, mark read, unread count | 🟢 Passing | 5 / 5 OK |
| **Notifications** | `notifications/tests/test_security.py` | Recipient data isolation, cross-user mark-read IDOR block, unauthenticated block | 🟢 Passing | 3 / 3 OK |

---

## ⚠️ Known Blockers & Technical Debt

*All identified issues resolved:*
- `utilities/__init__.py` import error: resolved.
- `AUTH_USER_MODEL = 'users.User'`: registered and active.
- PostgreSQL dev container running on port 5431 and connected via `.env`.
- Relational store multi-tenancy applied across Categories, Products, Cards, Inventory, Orders, Purchases, and Reports.
- N+1 query vulnerability in order listing eliminated by adding `select_related('customer', 'store')`.
- Product offer calculation updated to strictly use Python `Decimal` values, preventing `float` operand type errors.
- Decimal and cash collection status decoupled from fulfillment lifecycle state machine.
- Safe O(1) version invalidation eliminates expensive Redis wildcard `KEYS *` operations.
- Avoided View.dispatch collision by naming custom action `dispatch_order(url_path='dispatch')`.

---

## 📝 Changelog & Feature Milestones

### 2026-10-24
- Implemented **Phase 14: Order Fulfillment Lifecycle Pipeline**:
  - Added `preparing_at` and `dispatched_at` timestamps to `Order`.
  - Added `ORDER_PREPARING`, `ORDER_READY_FOR_PICKUP`, `ORDER_OUT_FOR_DELIVERY` to `NotificationType`.
  - Implemented `start_preparing` (`POST /orders/{id}/prepare/`) and `dispatch_order` (`POST /orders/{id}/dispatch/`) in `OrderService` and `OrderViewSet`.
  - Added actor-specific cancellation rules: customer cannot cancel once order preparation begins.
  - Added `test_fulfillment_pipeline.py` (5/5 passing).
- Implemented **Phase 15: Draft Memo Item Management & Tenant Security**:
  - Implemented `Product.is_offer_active` and `Product.effective_price` for dynamic time-bounded pricing.
  - Enforced `IsAuthenticated` and customer tenant scoping on `CardViewSet`.
  - Implemented `GET /cards/active/`, `POST /cards/{id}/add-item/`, `POST /cards/{id}/update-item/`, `POST /cards/{id}/remove-item/`, and `POST /cards/{id}/clear/`.
  - Automated store unbinding when draft memo becomes empty, allowing customer to transition to another store.
  - Added authoritative catalog price and offer revalidation at checkout in `OrderService.submit_order_from_card`.
  - Added `test_memo_management.py` (5/5 passing).
- Implemented **Phase 16: Authentication Lifecycle & User Profile Management**:
  - Implemented token authentication, login, logout, password change with token rotation, and profile management with strict tenant isolation.
  - Added `test_user_lifecycle.py` (13/13 passing).
- Implemented **Phase 17: Platform Administration & Store Governance**:
  - Implemented administrative store verification, suspension, reactivation, unverified checkout protection, and governance overview metrics.
  - Added `test_platform_admin.py` (12/12 passing).
- Implemented **Phase 18: Audit Logging & Activity Trail**:
  - Created `AuditLog` immutable append-only ledger for all critical actions with actor snapshot, IP, and diff metadata.
  - Added `test_audit_logging.py` (13/13 passing).
- Implemented **Phase 19: Production Rate Limiting & Abuse Controls**:
  - Created custom scoped throttles for authentication and nearby discovery endpoints with custom 429 response structure and retry delay metadata.
  - Added `test_throttling.py` (3/3 passing).
- Implemented **Phase 20: Customer Saved Delivery Addresses & Dynamic Distance-Based Delivery Fees**:
  - Implemented `CustomerAddress` model with soft deletion, single default address invariant, coordinate validation, dynamic tiered Haversine delivery fee quotes, and checkout address snapshotting.
  - Added `test_delivery_addresses.py` (10/10 passing).
- Implemented **Phase 21: Physical Inventory Audit & Batch Stock Reconciliation**:
  - Implemented `StockReconciliation` and `StockReconciliationItem` models, draft count sessions, variance valuation, atomic batch application with row locking, ledger entry logging, and cache invalidation.
  - Added `test_reconciliation.py` (8/8 passing).
- Implemented **Phase 22: Verified Customer Store Reviews & Ratings**:
  - Implemented `StoreReview` model with completed order verification, single-review per customer anti-spam guard, instant O(1) store average rating aggregation, vendor reply capability, and staff moderation.
  - Added `test_reviews.py` (10/10 passing).
- Implemented **Phase 23: Store Promotional Coupons & Order Discounts**:
  - Implemented `Coupon` and `CouponUsage` models with percentage discounts (and maximum ceiling caps), flat fixed currency amounts, min order amounts, time-bounded dates, and per-customer usage limits.
  - Implemented customer draft memo coupon attachment (`POST /cards/{id}/apply-coupon/`) and detachment (`POST /cards/{id}/remove-coupon/`) with live discount and estimated total preview.
  - Integrated authoritative server-side checkout discount calculation, immutable order and sales memo snapshots, atomic usage tracking, and vendor coupon management endpoints (`/stores/{id}/coupons/`, `/stores/coupons/{id}/`).
- Implemented **Phase 24: Delivery Driver Assignment & Real-Time Dispatch Tracking**:
  - Added delivery driver assignment fields to `Order` (`delivery_person_name`, `delivery_person_phone`, `delivery_vehicle_type`, `delivery_tracking_notes`, `delivery_assigned_at`, `estimated_delivery_time`).
  - Implemented `POST /orders/{id}/assign-delivery/` endpoint with auto-dispatch capability (`auto_dispatch=True` advancing status to `OUT_FOR_DELIVERY`), pickup and terminal order guards, and real-time customer notifications.
  - Exposed delivery driver contact info in `OrderSerializer` for customer tracking while strictly isolating assignment controls to store vendors.
  - Added `test_delivery_assignment.py` (9/9 passing).
- Implemented **Phase 25: Multi-Store Memo Cards & In-Store Walk-In Shopping**:
  - Enhanced `Card` model with `shopping_mode` (`walk_in` vs `remote`) and notes.
  - Implemented multi-store parallel draft cards, allowing customers to enter any store and maintain distinct, simultaneous shopping memos across different stores (`GET /cards/active/?store_id=<id>`, `POST /stores/{id}/memo/`).
  - Added `WALK_IN = 'walk_in', 'In-Store Walk-In Handover'` to `FulfillmentType`.
  - In-store walk-in shopping allows adding items while walking inside the store, checking out with zero delivery fee and no address required.
  - Implemented `POST /orders/{id}/handover/` allowing store owners to collect picked products, collect payment on spot, and hand them over directly at the counter, issuing the immutable `SalesMemo`.
- Implemented **Phase 26: Database-Level User & Vendor Fields Across Card & Memo Models**:
  - Added relational `user` (Customer) and `vendor` (Store Vendor) foreign keys directly to `Card` and `SalesMemo` with automatic backfill migrations and save hooks.
  - Added `test_database_level_fields.py` (6/6 passing).
- Implemented **Phase 27: Saved "Buy Next Time" Store Memos & Multi-Memo Planning**:
  - Added `is_saved_for_later` and `planned_visit_date` to `Card` model.
  - Implemented `create_saved_memo`, `save_memo_for_later`, `activate_saved_memo` (with safe merge), and `duplicate_memo` in `CardService`.
  - Added endpoints `GET /cards/saved/`, `POST /cards/create-saved/`, `POST /cards/{id}/save-for-later/`, `POST /cards/{id}/activate/`, and `POST /cards/{id}/duplicate/`.
  - Added `test_saved_memos.py` (7/7 passing).
- Implemented **Phase 28: In-Store Counter POS & Quick 6-Digit Walk-In Code Lookup**:
  - Added `walk_in_code` to `Order` (auto-generated 6-digit numeric verification code on walk-in / pickup order placement) and `walk_in_code_snapshot` to `SalesMemo`.
  - Added `OrderRepository.get_by_walk_in_code()` and `OrderService.counter_lookup()` with vendor tenant isolation.
  - Implemented `POST /orders/counter-lookup/` action on `OrderViewSet` enabling store owners / counter staff to instantly look up orders via 6-digit code.
  - Added `test_counter_pos.py` (7/7 passing).
- Implemented **Phase 29: Digital Sales Memo History, Thermal Receipt Formatting & Multi-Store Customer Spending Analytics**:
  - Implemented `SalesMemo.format_thermal_receipt()` 40-column monospace slip formatter with store header, memo #, order #, walk-in code snapshot, itemized breakdown, and totals.
  - Added `GET /orders/{id}/sales_memo/?receipt_format=thermal` and `GET /orders/{id}/thermal-receipt/` returning raw `text/plain` printable receipt slips.
  - Implemented `GET /orders/sales-memos/` digital receipt wallet with store ID, date range, search filters, pagination, and dual customer/vendor tenancy.
  - Implemented `GET /orders/customer-spending/` multi-store spending analytics computing `total_spent`, `total_saved`, `total_memos`, and `store_breakdown` using pure SQL database aggregations.
  - Added `test_sales_memos_and_spending.py` (7/7 passing).
- Implemented **Phase 30: In-Store Shelf Barcode Scanning, Walk-In Order QR Codes & Quick Memo Reordering**:
  - Added `barcode` field (`CharField(max_length=100, db_index=True)`) to `Product` model, serializer, and migration `products.0014_product_barcode_alter_product_sku`.
  - Added `ProductRepository.get_by_barcode_or_sku()` and `ProductService.lookup_by_barcode()` with store isolation.
  - Added public in-store shelf barcode lookup endpoint: `GET /products/api/barcode-lookup/?store_id=<id>&code=<code>`.
  - Integrated in-store physical shelf barcode scanner in customer draft shopping memos: `POST /cards/{id}/scan-add/` allowing customers to scan physical barcodes off store shelves to automatically add or increment line items in their draft memo.
  - Implemented standalone vector SVG QR code generation for walk-in verification: `Order.generate_qr_code_svg()`, `GET /orders/{id}/qr-code/`, and embedded data URI `qr_code_data_uri` in `OrderSerializer` for instant optical scanning at counter POS.
  - Implemented 1-tap quick reorder endpoint `POST /orders/{id}/reorder/` cloning past order items into an active draft shopping memo with live product availability, store status, and pricing re-validation.
- Implemented **Phase 31: In-Store Shelf Navigation, Aisle Route Organization & Basket Picking Checklist**:
  - Added `aisle` (`CharField(max_length=60, db_index=True)`) and `shelf_location` (`CharField(max_length=60)`) to `Product` model, serializer, and migration `products.0015_product_aisle_product_shelf_location`.
  - Added `is_picked` (`BooleanField(default=False, db_index=True)`) and `picked_at` (`DateTimeField(null=True)`) to `CardItem` model, serializer, and migration `cards.0008_carditem_is_picked_carditem_picked_at`.
  - Added real-time in-store shopping progress properties on `Card`: `total_items_count`, `picked_items_count`, `is_fully_picked`, and `picking_progress_percent`.
  - Implemented line item physical basket picking endpoint `POST /cards/{id}/toggle-item-picked/` and bulk picking endpoint `POST /cards/{id}/batch-pick/`.
  - Implemented in-store walking aisle route sorting (`GET /cards/{id}/?sort_by=aisle` and `GET /cards/active/?store_id=<id>&sort_by=aisle`) sequencing products by physical store layout (`product__aisle`, `product__shelf_location`).
  - Added automated test suite: `test_aisle_picking.py` (6/6 passing).
- Implemented **Phase 32: Cross-Store Memo Comparison, Store Transfer & Shopping Budget Controls**:
  - Added `budget_limit` (`DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)`) to `Card` model, serializer, and migration `cards.0009_card_budget_limit`.
  - Added dynamic budget calculation properties on `Card`: `budget_remaining`, `is_over_budget`, and `budget_used_percent`.
  - Implemented budget management endpoint `PATCH /cards/{id}/set-budget/` in `CardViewSet` and `CardService.set_budget_limit()`.
  - Implemented cross-store shopping memo comparison endpoint `POST /cards/{id}/compare-store/` via `CardService.compare_with_store()` resolving items by **Barcode -> SKU -> Case-Insensitive Product Name**, calculating price variances, total potential savings, missing items, and fulfillment feasibility.
  - Implemented store memo transfer endpoint `POST /cards/{id}/transfer-store/` via `CardService.transfer_to_store()` re-binding items to target store catalog, updating store and vendor foreign keys, clearing store-specific coupons, and supporting `omit_missing` and `clone` options.
  - Added automated test suite: `test_store_comparison_and_budget.py` (5/5 passing).
- Implemented **Phase 33: Store-Scoped Customer Loyalty Points, Visit Stamp Cards & Memo Reward Redemption**:
  - Implemented `StoreLoyaltyProgram`, `CustomerStoreLoyalty`, and append-only `LoyaltyTransaction` models with `POINTS` and `STAMPS` program types.
  - Added loyalty fields to `Card`: `loyalty_points_redeemed`, `loyalty_stamps_redeemed`, `loyalty_discount_amount`, and updated dynamic `estimated_total`.
  - Added loyalty tracking to `Order` and `SalesMemo`: `loyalty_points_redeemed`, `loyalty_discount_amount`, `loyalty_points_earned`, `loyalty_stamps_earned`.
  - Implemented `LoyaltyRepository` and `LoyaltyService` with atomic boundaries and row locking.
  - Added draft memo loyalty redemption: `POST /cards/{id}/redeem-loyalty/` and `POST /cards/{id}/remove-loyalty/`.
  - Connected authoritative checkout debit in `OrderService.submit_order_from_card` and automated refund in `OrderService.cancel_order`.
  - Automated point/stamp accrual upon order completion in `OrderService.fulfill_order` and in-store walk-in handover, snapshotting into `SalesMemo` and 40-col thermal receipt format.
  - Exposed vendor program management (`GET / PATCH /stores/{id}/loyalty-program/`, `GET /stores/{id}/loyalty-customers/`) and customer wallet (`GET /stores/{id}/loyalty/`, `GET /users/loyalty-cards/`).
  - Added automated test suite: `test_store_loyalty.py` (6/6 passing).
- Implemented **Phase 34: Customer Order Item Returns, Restocking & Thermal Credit Notes**:
  - Implemented `OrderReturn` and `OrderReturnItem` models with `ReturnStatus` (`REQUESTED`, `APPROVED`, `REJECTED`, `PROCESSED`) and `ReturnReason` choices.
  - Implemented `format_credit_note_thermal()` producing 40-column monospaced printable thermal slips.
  - Added atomic return processing in `OrderReturnService`: restoring inventory with `StockMovementType.RETURN` (or `DAMAGE_LOSS` if defective), proportional reversal of loyalty points/stamps (`LoyaltyTransactionType.RETURN_REVERSAL`), payment status updating to `REFUNDED`, and store catalog cache invalidation.
  - Exposed endpoints: `POST /orders/returns/request/`, `GET /orders/returns/`, `POST /orders/returns/{id}/process/`, and `GET /orders/returns/{id}/credit-note/?receipt_format=text`.
  - Added automated test suite: `test_order_returns.py` (8/8 passing).
- Implemented **Phase 35: Production CI/CD Pipeline & Database Backup/Restore Automation**:
  - Configured `.github/workflows/ci.yml` running linting (Ruff), security scanning (Bandit), migration verification, and automated test execution against PostgreSQL 15 and Redis 7.
  - Created automated database backup script `scripts/backup_db.sh` with gzip compression, SHA-256 checksums, and 30-day retention pruning.
  - Created automated database restore script `scripts/restore_db.sh` with integrity verification and safety confirmation.
- Implemented **Phase 36: Inter-Store Stock Transfers, Atomic Transit Ledger & Thermal Waybill Generation**:
  - Implemented `StockTransfer` and `StockTransferItem` models with `TransferStatus` (`DRAFT`, `IN_TRANSIT`, `RECEIVED`, `CANCELLED`).
  - Added movement types: `StockMovementType.TRANSFER_OUT`, `TRANSFER_IN`, and `TRANSFER_CANCEL_RESTORE`.
  - Implemented `StockTransferService` with pessimistic row locking (`select_for_update`), atomic stock deduction at dispatch, auto-provisioning or matching of products at destination on receive, safe stock rollback on cancellation, and driver thermal waybill generation (`format_waybill_thermal()`).
  - Exposed endpoints: `POST /inventory/transfers/create-transfer/`, `POST /inventory/transfers/{id}/dispatch/`, `POST /inventory/transfers/{id}/receive/`, `POST /inventory/transfers/{id}/cancel/`, and `GET /inventory/transfers/{id}/waybill/?receipt_format=text`.
  - Added automated test suite: `test_stock_transfers.py` (8/8 passing).
- Implemented **Phase 37: Perishable Batch & Expiry Date Tracking (FEFO), Spoilage Write-Off & Clearance Pricing**:
  - Implemented `ProductBatch` model with `store`, `product`, `batch_number`, `manufacture_date`, `expiry_date`, `initial_quantity`, `current_quantity`, `cost_price`, `status` (`ACTIVE`, `NEAR_EXPIRY`, `EXPIRED`, `DEPLETED`, `DISPOSED`), `is_clearance`, and `clearance_discount_percent`.
  - Added `StockMovementType.BATCH_DISPOSAL`, `NotificationType.BATCH_EXPIRY_ALERT`, and audit actions `BATCH_CREATED`, `BATCH_DISPOSED`, `BATCH_CLEARANCE`.
  - Implemented `BatchRepository` and `BatchService` for First-Expired, First-Out (FEFO) stock allocation, batch intake, atomic spoilage write-offs protecting active order reservations, dynamic clearance pricing, and near-expiry automated vendor alerting.
  - Exposed endpoints: `GET / POST /inventory/batches/`, `GET /inventory/batches/{id}/`, `POST /inventory/batches/{id}/dispose/`, `POST /inventory/batches/{id}/clearance/`, `GET /inventory/batches/near-expiry/`, and `POST /inventory/batches/fefo-allocate/`.
  - Added automated test suite: `test_product_batches.py` (10/10 passing).
- Executed full test suite across entire SaaS platform: **274 / 274 tests passing (100% pass rate)**.

---

## 📝 Changelog & Feature Milestones

### 2026-10-23
- Initial architectural analysis and domain model specification created.
- Created `security-testing` and updated `testing` skills.
- Implemented `Store` multi-tenant anchor model, repository, service, serializer, and viewset with tenant isolation.
- Scoped `Category` and `Product` models to `Store`, fixing FK constraints and adding catalog search.
- Implemented `inventory` app with `StockBalance`, check constraints, row-locking `select_for_update()`, and immutable `StockLedgerEntry`.
- Enhanced `cards` app with store scoping, single-store draft validation, and stock preservation.
- Implemented `orders` app with complete state machine (`SUBMITTED -> ACCEPTED -> COMPLETED / CANCELLED`), atomic stock reservations, fulfillment conversion, idempotency deduplication, and immutable `SalesMemo` generation.
- Implemented `purchases` app: store-scoped `Supplier` directory, `Purchase` order workflow (`DRAFT -> SUBMITTED -> RECEIVED`), atomic receipt into `StockBalance` with audit ledger logging, and anti-duplicate guards.
- Implemented `reports` app: vendor analytics engine computing gross sales, net product revenue, delivery fee totals, COD collected vs outstanding, inventory low-stock alerts, and procurement costs.
- Added N+1 query prevention tests (`assertNumQueries`) ensuring O(1) query-bounded API operations.
- Executed full test suite: **54 tests passing**.
