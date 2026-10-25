# Smart Memo System — Backend & Frontend Synchronization Tracker

> **Single Source of Truth** for tracking backend changes, API evolution, and frontend UI/state synchronization across the Smart Memo SaaS ecosystem.
> Whenever a backend feature, model, migration, or endpoint is added or updated, this tracker ensures the frontend is correspondingly updated without drift.

---

## 🔗 Repository Reference Links
- **Backend Repository Path**: [`/home/mizan/Desktop/smart_memo`](file:///home/mizan/Desktop/smart_memo)
  - Tech Stack: Python 3.12, Django 5.2, Django REST Framework, PostgreSQL 15, Redis 7
  - Local Server: `http://127.0.0.1:8000`
- **Frontend Repository Path**: [`/home/mizan/Desktop/Smart_Memo_Frontend`](file:///home/mizan/Desktop/Smart_Memo_Frontend)
  - Tech Stack: React 18 (Vite), Bootstrap 5, Bootstrap Icons, Lucide-React, Axios
  - Local Dev Server: `http://localhost:5173`
  - Design Palette: Brand Purple `#260E5E`, Midnight Dark `#0B0F19`, Pure White `#FFFFFF`

---

## 🔄 Backend-to-Frontend Sync Protocol

Whenever you update or introduce a feature in the backend:
1. **Record the Backend Change**: Add the new phase/endpoint/model in the matrix below with status 🟡 **PENDING FRONTEND**.
2. **Expose in Frontend API Client**: Add the corresponding request function in [`Smart_Memo_Frontend/src/api/index.js`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/api/index.js).
3. **Connect State & Context**: If the data affects global shopper or merchant state, update [`AuthContext`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/context/AuthContext.jsx), [`MemoContext`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/context/MemoContext.jsx), or [`ToastContext`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/context/ToastContext.jsx).
4. **Implement / Update UI Components & Pages**: Build or enhance corresponding pages in `src/pages/customer/`, `src/pages/vendor/`, or `src/pages/admin/`.
5. **Verify Build**: Run `npm --prefix /home/mizan/Desktop/Smart_Memo_Frontend run build` to verify clean compilation with 0 errors.
6. **Mark Synchronized**: Update the status to 🟢 **SYNCHRONIZED**.

---

## 📊 Comprehensive Feature Synchronization Matrix

| Phase | Feature Domain | Backend Model(s) | Backend API Endpoints | Frontend API Methods (`src/api/index.js`) | Frontend Components / Pages | Sync Status |
|:---:|:---|:---|:---|:---|:---|:---:|
| **1** | **Identity, Auth & Roles** | `User` (email, role: customer, vendor, staff) | `POST /users/register/`<br>`POST /users/login/`<br>`POST /users/logout/` | `authApi.register`<br>`authApi.login`<br>`authApi.logout` | [`LoginPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/common/LoginPage.jsx)<br>[`RegisterPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/common/RegisterPage.jsx)<br>[`AuthContext.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/context/AuthContext.jsx) | 🟢 SYNCHRONIZED |
| **2** | **Profile & Delivery Addresses** | `CustomerAddress` (is_default, coordinates) | `GET / PATCH /users/profile/`<br>`POST /users/change-password/`<br>`GET / POST / DELETE /users/addresses/` | `authApi.getProfile`<br>`authApi.updateProfile`<br>`authApi.changePassword`<br>`authApi.getAddresses`<br>`authApi.createAddress`<br>`authApi.deleteAddress` | [`ProfilePage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/common/ProfilePage.jsx) | 🟢 SYNCHRONIZED |
| **3** | **Store Management & Discovery** | `Store` (vendor FK, hours, delivery fee, min order) | `GET /stores/`<br>`GET /stores/{id}/`<br>`POST /stores/{id}/memo/` | `storesApi.getStores`<br>`storesApi.getStoreDetail`<br>`storesApi.enterStoreMemo` | [`StoreDiscoveryPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/StoreDiscoveryPage.jsx)<br>[`StoreDetailPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/StoreDetailPage.jsx) | 🟢 SYNCHRONIZED |
| **4** | **Nearby Geolocation & Favorites** | `FavoriteStore` (customer FK, store FK) | `GET /stores/nearby/`<br>`GET /stores/favorites/`<br>`POST /stores/{id}/favorite/` | `storesApi.getNearbyStores`<br>`storesApi.getFavorites`<br>`storesApi.toggleFavorite` | [`StoreDiscoveryPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/StoreDiscoveryPage.jsx)<br>Compass Geolocation Button | 🟢 SYNCHRONIZED |
| **5** | **Catalog, Aisles & Shelf Tags** | `Category`, `Product` (aisle, shelf, barcode, SKU) | `GET /categories/`<br>`GET /products/`<br>`POST /products/` | `catalogApi.getCategories`<br>`catalogApi.getProducts`<br>`catalogApi.createProduct` | [`ProductCatalogPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/ProductCatalogPage.jsx)<br>Thermal Tag Generator | 🟢 SYNCHRONIZED |
| **6** | **In-Store Shelf Barcode Scanner** | `Product` (barcode, sku) | `GET /products/api/barcode-lookup/`<br>`POST /cards/{id}/scan-add/` | `catalogApi.lookupBarcode`<br>`memoApi.scanAddItem` | [`BarcodeScannerModal.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/components/common/BarcodeScannerModal.jsx)<br>Global Navbar trigger | 🟢 SYNCHRONIZED |
| **7** | **Multi-Store Draft Shopping Memos** | `Card`, `CardItem` (user, vendor, store FKs) | `GET /cards/active/`<br>`POST /cards/{id}/add-item/`<br>`POST /cards/{id}/update-item/`<br>`POST /cards/{id}/remove-item/`<br>`POST /cards/{id}/clear/` | `memoApi.getActiveMemo`<br>`memoApi.addItem`<br>`memoApi.updateItem`<br>`memoApi.removeItem`<br>`memoApi.clearMemo` | [`ActiveMemoPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/ActiveMemoPage.jsx)<br>[`MemoContext.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/context/MemoContext.jsx) | 🟢 SYNCHRONIZED |
| **8** | **In-Store Aisle Route & Basket Picking** | `CardItem` (is_picked, picked_at) | `GET /cards/{id}/?sort_by=aisle`<br>`POST /cards/{id}/toggle-item-picked/`<br>`POST /cards/{id}/batch-pick/` | `memoApi.getMemoDetail`<br>`memoApi.toggleItemPicked`<br>`memoApi.batchPick` | [`ActiveMemoPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/ActiveMemoPage.jsx)<br>Aisle Walking Sequence toggle | 🟢 SYNCHRONIZED |
| **9** | **Shopping Budget Limits** | `Card` (budget_limit, is_over_budget) | `POST /cards/{id}/set-budget/` | `memoApi.setBudget` | [`ActiveMemoPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/ActiveMemoPage.jsx)<br>Budget Progress Bar | 🟢 SYNCHRONIZED |
| **10** | **Cross-Store Price Comparison & Transfer** | `Product` matching (barcode -> sku -> name) | `POST /cards/{id}/compare-store/`<br>`POST /cards/{id}/transfer-store/` | `memoApi.compareStore`<br>`memoApi.transferStore` | [`ActiveMemoPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/ActiveMemoPage.jsx)<br>Compare Modal & 1-tap Transfer | 🟢 SYNCHRONIZED |
| **11** | **Store Routine Basket Templates** | `StoreMemoTemplate`, `StoreMemoTemplateItem` | `POST /cards/{id}/save-as-template/`<br>`GET / POST /cards/templates/`<br>`DELETE /cards/templates/{id}/`<br>`POST /cards/templates/{id}/load-to-memo/` | `memoApi.saveAsTemplate`<br>`memoApi.getTemplates`<br>`memoApi.createTemplate`<br>`memoApi.deleteTemplate`<br>`memoApi.loadTemplateToMemo` | [`SavedMemosPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/SavedMemosPage.jsx)<br>One-Tap Hydration (`replace`/`merge`) | 🟢 SYNCHRONIZED |
| **12** | **"Buy Next Time" Planned Memos** | `Card` (is_saved_for_later, planned_visit_date) | `GET /cards/saved/`<br>`POST /cards/create-saved/`<br>`POST /cards/{id}/save-for-later/`<br>`POST /cards/{id}/activate/` | `memoApi.getSavedMemos`<br>`memoApi.createSavedMemo`<br>`memoApi.saveForLater`<br>`memoApi.activateSavedMemo` | [`SavedMemosPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/SavedMemosPage.jsx)<br>Planning Tab | 🟢 SYNCHRONIZED |
| **13** | **Promotional Coupons & Discounts** | `Coupon`, `CouponUsage` | `GET / POST /stores/{id}/coupons/`<br>`POST /cards/{id}/apply-coupon/`<br>`POST /cards/{id}/remove-coupon/` | `storesApi.getCoupons`<br>`storesApi.createCoupon`<br>`memoApi.applyCoupon`<br>`memoApi.removeCoupon` | [`ActiveMemoPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/ActiveMemoPage.jsx)<br>[`LoyaltyManagerPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/LoyaltyManagerPage.jsx) | 🟢 SYNCHRONIZED |
| **14** | **Store Loyalty Points & Visit Stamps** | `StoreLoyaltyProgram`, `CustomerStoreLoyalty` | `GET / POST /stores/{id}/loyalty/`<br>`POST /cards/{id}/redeem-loyalty/`<br>`POST /cards/{id}/remove-loyalty/` | `storesApi.getLoyaltyProgram`<br>`storesApi.saveLoyaltyProgram`<br>`memoApi.redeemLoyalty`<br>`memoApi.removeLoyalty` | [`ActiveMemoPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/ActiveMemoPage.jsx)<br>[`LoyaltyManagerPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/LoyaltyManagerPage.jsx) | 🟢 SYNCHRONIZED |
| **15** | **Dual-Mode Checkout & 6-Digit Walk-In Code** | `Order` (walk_in_code, fulfillment_type) | `POST /cards/{id}/checkout/`<br>`POST /stores/{id}/calculate-delivery-fee/` | `memoApi.checkout`<br>`storesApi.calculateDeliveryFee` | [`CheckoutPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/CheckoutPage.jsx)<br>[`WalkInCodeBadge.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/components/common/WalkInCodeBadge.jsx) | 🟢 SYNCHRONIZED |
| **16** | **In-Store Counter POS Terminal** | `Order` (walk-in 6-digit code verification) | `POST /orders/counter-lookup/`<br>`POST /orders/{id}/handover/` | `ordersApi.counterLookup`<br>`ordersApi.handoverOrder` | [`CounterPOSPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/CounterPOSPage.jsx)<br>Touchscreen Keypad | 🟢 SYNCHRONIZED |
| **17** | **Order Fulfillment & Driver Dispatch** | `Order` (status machine, delivery driver assignment) | `POST /orders/{id}/accept/`<br>`POST /orders/{id}/prepare/`<br>`POST /orders/{id}/dispatch/`<br>`POST /orders/{id}/fulfill/`<br>`POST /orders/{id}/assign-delivery/` | `ordersApi.acceptOrder`<br>`ordersApi.prepareOrder`<br>`ordersApi.dispatchOrder`<br>`ordersApi.fulfillOrder`<br>`ordersApi.assignDelivery` | [`VendorOrdersPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/VendorOrdersPage.jsx)<br>Driver Assignment Modal | 🟢 SYNCHRONIZED |
| **18** | **Customer Order Tracking & Driver Details** | `Order` (driver phone, vehicle, tracking notes) | `GET /orders/`<br>`GET /orders/{id}/` | `ordersApi.getOrders`<br>`ordersApi.getOrderDetail` | [`OrderHistoryPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/OrderHistoryPage.jsx)<br>Real-time Stepper & Call Driver | 🟢 SYNCHRONIZED |
| **19** | **Digital Sales Memo Wallet & Thermal Slips** | `SalesMemo` (monospace 40-col ASCII layout) | `GET /orders/sales-memos/`<br>`GET /orders/{id}/thermal-receipt/` | `ordersApi.getSalesMemos`<br>`ordersApi.getThermalReceipt` | [`SalesMemoWalletPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/SalesMemoWalletPage.jsx)<br>[`ThermalReceiptModal.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/components/common/ThermalReceiptModal.jsx) | 🟢 SYNCHRONIZED |
| **20** | **Multi-Store Customer Spending Analytics** | SQL Aggregations (`Coalesce(Sum(...))`) | `GET /orders/customer-spending/` | `ordersApi.getCustomerSpending` | [`SalesMemoWalletPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/SalesMemoWalletPage.jsx)<br>Spent / Saved / Store breakdown | 🟢 SYNCHRONIZED |
| **21** | **Item Returns, Restock & Credit Notes** | `OrderReturn`, `OrderReturnItem` | `POST /orders/returns/request/`<br>`GET /orders/returns/`<br>`POST /orders/returns/{id}/process/`<br>`GET /orders/returns/{id}/credit-note/` | `ordersApi.requestReturn`<br>`ordersApi.getReturns`<br>`ordersApi.processReturn`<br>`ordersApi.getCreditNote` | [`ReturnsManagerPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/ReturnsManagerPage.jsx)<br>Print Credit Note Slip | 🟢 SYNCHRONIZED |
| **22** | **Inventory Balances & Batch Reconciliation** | `StockBalance`, `StockReconciliation` | `GET /inventory/balances/`<br>`GET / POST /inventory/reconciliations/`<br>`POST /inventory/reconciliations/{id}/apply/` | `vendorApi.getInventoryBalances`<br>`vendorApi.getReconciliations`<br>`vendorApi.applyReconciliation` | [`InventoryPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/InventoryPage.jsx) | 🟢 SYNCHRONIZED |
| **23** | **Supplier Directory & Purchase Orders** | `Supplier`, `Purchase`, `PurchaseItem` | `GET /purchases/suppliers/`<br>`GET /purchases/`<br>`POST /purchases/{id}/receive/` | `vendorApi.getSuppliers`<br>`vendorApi.getPurchases`<br>`vendorApi.receivePurchase` | [`PurchasesPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/PurchasesPage.jsx) | 🟢 SYNCHRONIZED |
| **24** | **Verified Customer Store Reviews & Replies** | `StoreReview` (rating, comment, vendor_reply) | `GET / POST /stores/{id}/reviews/`<br>`POST /stores/reviews/{id}/reply/` | `storesApi.getReviews`<br>`storesApi.createReview`<br>`storesApi.replyReview` | [`StoreDetailPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/StoreDetailPage.jsx)<br>Reviews Tab | 🟢 SYNCHRONIZED |
| **25** | **Platform Governance & Store Moderation** | `Store` (is_verified, is_active, suspension) | `GET /stores/governance-overview/`<br>`POST /stores/{id}/verify/`<br>`POST /stores/{id}/suspend/`<br>`POST /stores/{id}/activate/` | `adminApi.getGovernanceOverview`<br>`adminApi.verifyStore`<br>`adminApi.suspendStore`<br>`adminApi.activateStore` | [`GovernancePage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/admin/GovernancePage.jsx) | 🟢 SYNCHRONIZED |
| **26** | **Immutable Activity Trail & Audit Logs** | `AuditLog` (append-only ledger) | `GET /audit/logs/` | `adminApi.getAuditLogs` | [`AuditLogsPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/admin/AuditLogsPage.jsx) | 🟢 SYNCHRONIZED |
| **27** | **Vendor Analytics & Revenue Reports** | Database Aggregations | `GET /reports/vendor-summary/` | `vendorApi.getReports` | [`VendorDashboardPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/VendorDashboardPage.jsx) | 🟢 SYNCHRONIZED |
| **28** | **Store Public Branding & Standalone Merchant Website URLs** | `Store` (`owner_name`, `logo_url`, `cover_photo_url`, `secondary_phone`, `whatsapp_number`, `website_url`, `social_links`, `shop_type`, `public_url_slug`) | `GET /stores/public-store/{slug_or_domain}/`<br>`PATCH /stores/{id}/` | `storesApi.getPublicStorefront`<br>`storesApi.updateStore` | [`PublicStorefrontPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/PublicStorefrontPage.jsx)<br>[`VendorDashboardPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/VendorDashboardPage.jsx) | 🟢 SYNCHRONIZED |
| **29** | **Product Multiple Gallery Images & Showcase Photos** | `ProductImage` (`is_primary`, `display_order`, `alt_text`), `Product.primary_image_url` | `GET / POST /products/{id}/images/`<br>`DELETE / POST /products/{id}/images/{image_id}/` | `catalogApi.getProductImages`<br>`catalogApi.addProductImage`<br>`catalogApi.deleteProductImage`<br>`catalogApi.setPrimaryProductImage` | [`ProductCatalogPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/ProductCatalogPage.jsx)<br>[`PublicStorefrontPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/PublicStorefrontPage.jsx) | 🟢 SYNCHRONIZED |
| **30** | **Vendor Store Branding Hero, Hot Products (Bestsellers) & Order Status Lifecycle** | `Store`, `Order` (status machine), `OrderItem`, `Product` | `GET /reports/vendor-summary/?store_id=`<br>`GET /orders/?as_vendor=true`<br>`POST /orders/{id}/accept/`<br>`POST /orders/{id}/prepare/`<br>`POST /orders/{id}/dispatch/`<br>`POST /orders/{id}/fulfill/`<br>`POST /orders/{id}/cancel/` | `vendorApi.getReports`<br>`ordersApi.getOrders`<br>`ordersApi.acceptOrder`<br>`ordersApi.prepareOrder`<br>`ordersApi.dispatchOrder`<br>`ordersApi.fulfillOrder`<br>`ordersApi.cancelOrder` | [`VendorDashboardPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/VendorDashboardPage.jsx)<br>Cover/Profile Banner, Hot Products Tab, Order Lifecycle Action Buttons | 🟢 SYNCHRONIZED |
| **31** | **Vendor Custom Categories, Product Creation Under Category, and Overall & Category-Wise Sales Reports & Charts** | `Category` (store FK), `Product` (category FK, tenant validation), `OrderItem`, `Order` | `GET / POST /categories/`<br>`GET / POST /categories/api/`<br>`POST /products/`<br>`GET /reports/category-sales/?store_id=`<br>`GET /reports/sales-trends/?store_id=&days=` | `catalogApi.getCategories`<br>`catalogApi.createCategory`<br>`catalogApi.createProduct`<br>`vendorApi.getCategorySales`<br>`vendorApi.getSalesTrends` | [`VendorDashboardPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/VendorDashboardPage.jsx)<br>[`ProductCatalogPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/ProductCatalogPage.jsx)<br>Category Creator Modal, Product under Category Modal, 14-Day Timeline Chart, Category Sales Distribution & Breakdown Ledger | 🟢 SYNCHRONIZED |
| **33** | **Modern Left-Aligned Executive Vendor Dashboard & UI Overhaul** | `Store`, `Order`, `Category`, `Product` | `GET /stores/`<br>`GET /reports/vendor-summary/`<br>`GET /reports/sales-trends/`<br>`GET /reports/category-sales/`<br>`GET /orders/?as_vendor=true`<br>`GET /categories/api/` | `storesApi.getStores`<br>`vendorApi.getReports`<br>`vendorApi.getSalesTrends`<br>`vendorApi.getCategorySales`<br>`ordersApi.getOrders`<br>`catalogApi.getCategories` | [`VendorDashboardPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/vendor/VendorDashboardPage.jsx)<br>Executive Gradient Left Sidebar, Quick Multi-Store Switcher, Glowing Metric KPI Cards, Sales Velocity Chart, Clean Deduplicated Tabs, Zero Emojis, 100% Vector SVG Icons | 🟢 SYNCHRONIZED |
| **34** | **Named Per-Store Memo Gate & Dual-Channel Payment Methods (COD / bKash / Nagad)** | `Card` (`title`, `shopping_mode`, `store` FK), `Order` (`payment_method`: `cod`, `cash_counter`, `bkash`, `nagad`) | `GET /stores/{id}/memo/?create=false` (peek, returns `null`)<br>`POST /stores/{id}/memo/` (`title`, `shopping_mode`)<br>`GET /cards/active/?store_id=&create=false`<br>`PATCH /cards/{id}/` (rename)<br>`POST /cards/{id}/checkout/` (`payment_method`, `address_id`, `notes`) | `storesApi.peekStoreMemo`<br>`storesApi.openStoreMemo`<br>`memoApi.getActiveMemo(storeId, mode, { create })`<br>`memoApi.renameMemo`<br>`memoApi.checkout` | [`MemoStartModal.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/components/customer/MemoStartModal.jsx)<br>[`MemoContext.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/context/MemoContext.jsx)<br>[`StoreDetailPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/StoreDetailPage.jsx)<br>[`PublicStorefrontPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/PublicStorefrontPage.jsx)<br>[`ActiveMemoPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/ActiveMemoPage.jsx)<br>[`CheckoutPage.jsx`](file:///home/mizan/Desktop/Smart_Memo_Frontend/src/pages/customer/CheckoutPage.jsx)<br>Name-Your-Memo Gate, Per-Store Memo Isolation, Inline Memo Rename, Payment Method Picker | 🟢 SYNCHRONIZED |

---

## 📌 Pending & Upcoming Feature Queue
When building a new backend feature, register it here first before coding:

| Proposed Phase | Proposed Feature | Target Backend Files | Target Frontend Files | Status |
|:---:|:---|:---|:---|:---:|
| **35** | **Shared Family Memo Collaboration** | `cards/models/collaborator_mod.py`<br>`cards/views/collaborator_view.py` | `src/components/customer/CollaboratorModal.jsx` | 💡 Planned |
| **36** | **Vendor Store Staff & Cashier Delegation** | `stores/models/staff_mod.py`<br>`stores/views/staff_view.py` | `src/pages/vendor/StoreStaffPage.jsx` | 💡 Planned |
| **37** | **Fractional Weight Produce Presets (kg/gm)** | `products/models/product_mod.py`<br>`cards/services/card_service.py` | `src/components/customer/WeightSelector.jsx` | 💡 Planned |
| **38** | **Daily Cash Register & Shift Closure** | `orders/models/cash_shift_mod.py`<br>`orders/views/pos_view.py` | `src/pages/vendor/CashDrawerPage.jsx` | 💡 Planned |

---

*Last Synchronized:* **2026-10-25** | *Backend Build Status:* **298/298 Tests Passing (100%)** | *Frontend Build Status:* **Clean (Vite 0 Errors)**

---

## 🧾 Phase 34 — Business Rules & Behavioral Contract

**Memo-first shopping gate**
- A customer must open a **named** memo for a store before any product can be added. Memos are no longer created implicitly on store entry.
- `GET .../memo/?create=false` and `GET /cards/active/?create=false` return `data: null` instead of opening a memo, letting the UI render the "Create Your Memo" prompt.
- `POST /stores/{id}/memo/` is idempotent per store: re-posting returns the **same** memo and applies any `title` / `shopping_mode` change rather than creating a duplicate.
- Memos remain strictly store-scoped. `CardService.add_product_to_card` still rejects items from a different store, and a peek for store B never surfaces store A's memo.

**Payment methods (UI-level stage)**
- `PaymentMethod`: `cod`, `cash_counter`, `bkash`, `nagad`.
- Mobile financial services (`bkash`, `nagad`) are accepted **only** for `fulfillment_type='delivery'`. Walk-in / pickup orders are settled in physical cash at the counter and are rejected with HTTP 400 if an online method is sent.
- No gateway integration yet: every method is recorded with `payment_status='pending'` and settled through the existing handover / delivery collection flow. Transaction-ID capture and provider verification remain open.

**Checkout contract fix**
- The React checkout form previously posted `fulfillment_type: 'home_delivery'`, `customer_address_id`, and `delivery_instructions`, none of which the API reads. Home delivery orders were therefore saved with an invalid status value, a blank `delivery_address`, zero delivery fee, and skipped `delivery_enabled` / `min_order_amount` validation. The form now posts `fulfillment_type: 'delivery'`, `address_id`, and `notes`.

**Store-scoped product listing**
- `GET /products/?store_id=` previously ignored `store_id` and returned **every** store's active products, so a store page advertised items that `add-item` necessarily rejected with "All items in a shopping memo must belong to the same store." `ProductViewSet.get_queryset` now honours `store_id` and `category_id`; vendors still cannot widen scope past their own stores.

**Other frontend defects fixed alongside**
- `StoreDetailPage` passed the whole product object where `addToMemo` expects a product id, so `product_id` was posted as an object.
- `StoreDetailPage` linked to `/memo`, which is not a route (`/active-memo` is) and fell through to the catch-all redirect.
- `PublicStorefrontPage` destructured `setDrawerOpen` from `MemoContext`, which never provided it — calling it threw after a successful add. The page now owns its own `MemoDrawer`.
- `ActiveMemoPage` read `activeMemo.subtotal` and `activeMemo.loyalty_discount`, neither of which `CardSerializer` emits, rendering "Items Subtotal $0.00" beside a non-zero total. Now uses `total_price` / `estimated_total` / `loyalty_discount_amount`.

**Tests**: `cards/tests/test_named_memo_and_payment.py` (13 cases) covers the memo gate, cross-store isolation, cross-customer leakage, payment-method policy, and the exact payload the frontend sends. `products/tests/test_catalog_store_scope.py` (3 cases) covers store-scoped product listing.

**Verified end to end** against the dev stack: a bKash home-delivery order (`delivery` / `bkash`, address snapshotted, $4.50 fee applied, `min_order_amount` enforced) and a counter-cash walk-in order at a *different* store (`walk_in` / `cash_counter`, 6-digit code issued, zero fee), each against its own separately named memo.

---

## 🔐 Phase 35 — Authentication Hardening, Dead-Code Removal & UX Cleanup

**Session / login correctness**
- `AuthContext` trusted `localStorage` blindly: a persisted token was treated as a live session with no server check, so an expired or revoked token left the app "signed in" while every request 401'd. The provider now validates the token against `GET /users/me/` on boot, clears the session on 401/403, and deliberately **keeps** the session on a network error so a connectivity blip does not sign users out.
- `login()` never checked that the response contained a token. A malformed response stored the literal string `"undefined"`, leaving a permanently broken "logged in" state. It now throws instead.
- `isAuthenticated` was `!!token`, which could be true while `user` was `null` (corrupt cached user) — route guards admitted the request but every role check was false. It now requires both a token and a resolved identity, and the role flags derive from it.
- The 401 interceptor used `window.location.href`, hard-reloading the SPA and discarding the current page. It now dispatches a `smart-memo:unauthorized` event that `AuthContext` listens for, keeping React state and `localStorage` in step and letting the router handle the redirect.
- `GET /users/me/` already existed; it is now documented as the SPA's session-validation probe. Covered by `users/tests/test_current_user.py` (valid token, anonymous, revoked token).

**Removed (dead or unsafe surface)**
- **Silent mock-data fallback** in `src/api/client.js`: when the backend was unreachable the client fabricated stores, products, categories, coupons, templates and fake reviews with invented customer names, and returned them as if real. Users could browse a fully fictional catalog and never know the backend was down. Removed along with `src/api/mockData.js` (221 lines).
- **Hardcoded demo credentials**: the "Quick Fill Test Accounts" panel on the login page and the "Demo Role" switcher in the navbar both embedded real account emails and the shared password `Password123!` in shipped client code. Both removed, along with the now-unused handler and icon imports.
- A duplicate `me` action accidentally added to `UserViewSet` (shadowed by the pre-existing one) was removed rather than left as dead code.

**Fixed**
- Error messages: the API wraps failures as `{ message: "Validation error", errors: ["Invalid email or password."] }`. The client read `message` first, so every login failure surfaced the useless envelope label. It now reads `errors` first (array and field-map forms), falling back to `message`, and gives specific copy for network/timeout failures.
- Customer pages hand-rolled response unwrapping with differing fallback chains — the source of earlier `.map is not a function` crashes. `StoreDetailPage`, `OrderHistoryPage`, `PublicStorefrontPage`, `CheckoutPage` and `ActiveMemoPage` now use the shared `unwrapList` / `unwrapObject` helpers that the vendor pages already used.

**UX**
- Login: inline, persistent error alerts (a toast vanished before it could be read), password visibility toggle, `autoComplete` hints, labelled inputs, autofocus, and a "Signing in…" busy state.
- `ProtectedRoute` records the intended path and login returns the user there instead of dumping them on the home page.
- A role mismatch previously redirected to `/` with no explanation, which read as a broken link. It now renders an explicit "You don't have access to this page" card naming the required role, the signed-in account, and a link to that role's own dashboard.

**Verified**: 317 backend tests pass; frontend builds clean. Browser-checked end to end — protected-route redirect, wrong-password inline error, login returning to the originally requested page, session revalidation on reload, customer-blocked-from-vendor-console, and a stale token being cleared with a redirect to login.
