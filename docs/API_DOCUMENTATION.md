# Smart Memo System — REST API Documentation

This document defines the REST API contracts, schemas, headers, status codes, and response envelopes for the Smart Memo System SaaS.

---

## 1. Global Conventions

### Base URL
- **Development**: `http://localhost:8001/api/v1`
- **Production**: `https://api.smartmemo.local/api/v1`

### Standard Headers
| Header | Description | Required | Example |
|---|---|:---:|---|
| `Content-Type` | MIME type of request body | Yes for POST/PUT/PATCH | `application/json` |
| `Authorization` | JWT access token | Yes for authenticated endpoints | `Bearer eyJhbGciOi...` |
| `X-Store-Id` | Active store context (for vendors with multiple stores) | Optional / Vendor Endpoints | `1` |

### Standard Response Envelope
All API endpoints follow the consistent JSON envelope defined in [`shared/responses/responses.py`](file:///home/mizan/Desktop/smart_memo/shared/responses/responses.py):

#### Success Response (`200 OK`, `201 Created`):
```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": { ... },
  "errors": null
}
```

#### Paginated List Response:
```json
{
  "success": true,
  "message": "Data retrieved successfully.",
  "data": [ ... ],
  "pagination": {
    "count": 45,
    "total_pages": 5,
    "current_page": 1,
    "page_size": 10,
    "next": "http://localhost:8001/api/v1/catalog/products/?page=2",
    "previous": null,
    "has_next": true,
    "has_previous": false
  },
  "errors": null
}
```

#### Error Response (`400`, `401`, `403`, `404`, `429`, `500`):
```json
{
  "success": false,
  "message": "Validation failed.",
  "data": null,
  "errors": {
    "field_name": "Error description."
  }
}
```

---

## 2. Authentication & User APIs

### `POST /users/register/`
- **Description**: Registers a new customer or vendor.
- **Permissions**: Public (AllowAny).
- **Request Body**:
```json
{
  "email": "vendor@store.com",
  "password": "StrongPassword123!",
  "full_name": "Mizanur Rahman",
  "role": "VENDOR"
}
```
- **Response** (`201 Created`):
```json
{
  "success": true,
  "message": "User registered successfully.",
  "data": {
    "user": {
      "id": 1,
      "email": "vendor@store.com",
      "role": "VENDOR",
      "is_active": true,
      "created_at": "2026-10-24T14:30:00Z",
      "profile": {
        "full_name": "Mizanur Rahman",
        "phone_number": "",
        "address": "",
        "avatar": null
      }
    }
  },
  "errors": null
}
```

### `POST /users/login/`
- **Description**: Authenticates user against credentials and issues DRF auth token.
- **Permissions**: Public (AllowAny).
- **Request Body**:
```json
{
  "email": "vendor@store.com",
  "password": "StrongPassword123!"
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
    "user": {
      "id": 1,
      "email": "vendor@store.com",
      "role": "VENDOR",
      "is_active": true,
      "created_at": "2026-10-24T14:30:00Z",
      "profile": {
        "full_name": "Mizanur Rahman",
        "phone_number": "",
        "address": "",
        "avatar": null
      }
    }
  },
  "errors": null
}
```

### `POST /users/logout/`
- **Description**: Revokes the active auth token and invalidates the session.
- **Permissions**: IsAuthenticated (`Authorization: Token <token>`).
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Logout successful.",
  "data": null,
  "errors": null
}
```

### `POST /users/change-password/`
- **Description**: Updates user password after validating existing credentials and rotates auth token.
- **Permissions**: IsAuthenticated (`Authorization: Token <token>`).
- **Request Body**:
```json
{
  "old_password": "StrongPassword123!",
  "new_password": "BrandNewPassword999!"
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Password changed successfully.",
  "data": {
    "token": "new-rotated-token-key-12345"
  },
  "errors": null
}
```

### `GET /users/me/`
- **Description**: Retrieves authenticated user account details and profile.
- **Permissions**: IsAuthenticated.

### `GET /users/profile/`
- **Description**: Fetches current user profile details.
- **Permissions**: IsAuthenticated.
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Profile retrieved.",
  "data": {
    "profile": {
      "full_name": "Mizanur Rahman",
      "phone_number": "+8801700000000",
      "address": "House 12, Road 4, Uttara, Dhaka",
      "avatar": null
    }
  },
  "errors": null
}
```

### `PATCH /users/profile/`
- **Description**: Partially updates current user's profile with strict object isolation.
- **Permissions**: IsAuthenticated.
- **Request Body**:
```json
{
  "full_name": "Mizanur Rahman",
  "phone_number": "+8801700000000",
  "address": "House 12, Road 4, Uttara, Dhaka"
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Profile updated successfully.",
  "data": {
    "profile": {
      "full_name": "Mizanur Rahman",
      "phone_number": "+8801700000000",
      "address": "House 12, Road 4, Uttara, Dhaka",
      "avatar": null
    }
  },
  "errors": null
}
```


---

## 3. Store Management APIs

### `POST /api/v1/stores/`
- **Description**: Creates a new store managed by the authenticated vendor.
- **Permissions**: IsAuthenticated & IsVendor.
- **Request Body**:
```json
{
  "name": "Green Valley Grocery",
  "description": "Fresh produce and daily groceries",
  "phone_number": "+8801711111111",
  "email": "contact@greenvalley.com",
  "address": "House 12, Road 4, Sector 3, Uttara, Dhaka",
  "latitude": 23.8759,
  "longitude": 90.3795,
  "opening_time": "08:00:00",
  "closing_time": "22:00:00",
  "delivery_enabled": true,
  "pickup_enabled": true,
  "delivery_fee": "50.00",
  "min_order_amount": "200.00"
}
```

### `GET /stores/public/`
- **Description**: Discover active and verified stores.
- **Permissions**: Public.

### `GET /stores/nearby/`
- **Description**: Geospatial Haversine store discovery with radius filter and coordinate bounds check.
- **Permissions**: Public.

### `POST /stores/{id}/verify/`
- **Description**: Platform admin approves and verifies a store for public discovery and ordering.
- **Permissions**: IsStaffOrAdmin (Staff / Superuser).
- **Request Body**:
```json
{
  "notes": "Trade license and business documentation verified."
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Store verified successfully.",
  "data": {
    "store": {
      "id": 1,
      "name": "Green Valley Grocery",
      "is_active": true,
      "is_verified": true,
      "verified_at": "2026-10-24T14:40:00Z",
      "verification_notes": "Trade license and business documentation verified."
    }
  },
  "errors": null
}
```

### `POST /stores/{id}/suspend/`
- **Description**: Platform admin suspends a store, immediately disabling public discovery and orders.
- **Permissions**: IsStaffOrAdmin (Staff / Superuser).
- **Request Body**:
```json
{
  "reason": "Terms of service violation."
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Store suspended successfully.",
  "data": {
    "store": {
      "id": 1,
      "name": "Green Valley Grocery",
      "is_active": false,
      "is_verified": true,
      "verification_notes": "Terms of service violation."
    }
  },
  "errors": null
}
```

### `POST /stores/{id}/activate/`
- **Description**: Platform admin reactivates a suspended store.
- **Permissions**: IsStaffOrAdmin (Staff / Superuser).
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Store reactivated successfully.",
  "data": {
    "store": {
      "id": 1,
      "name": "Green Valley Grocery",
      "is_active": true,
      "is_verified": true
    }
  },
  "errors": null
}
```

### `GET /stores/governance-overview/`
- **Description**: Aggregated platform-wide metrics (stores breakdown, user distribution, GMV, orders status).
- **Permissions**: IsStaffOrAdmin (Staff / Superuser).
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Platform governance overview retrieved.",
  "data": {
    "overview": {
      "stores": {
        "total": 45,
        "active": 42,
        "verified": 40,
        "unverified": 5,
        "suspended": 3
      },
      "users": {
        "total_vendors": 38,
        "total_customers": 1520,
        "total_staff": 4
      },
      "orders": {
        "total": 840,
        "completed": 760,
        "active": 50,
        "cancelled": 30,
        "gross_merchandise_volume": "142580.00"
      }
    }
  },
  "errors": null
}
```


---

## 4. Category Management APIs

### `GET /api/v1/categories/`
- **Description**: List categories for the vendor's active store (or public for store ID).
- **Permissions**: IsStoreOwner (Vendor) / Public when filtering `?store_id=X`.
- **Query Parameters**:
  - `store_id` (int, optional for public catalog)
  - `page` (int, default: 1)

### `POST /api/v1/categories/`
- **Description**: Creates a store-scoped category.
- **Permissions**: IsStoreOwner.
- **Request Body**:
```json
{
  "name": "Fresh Fruits"
}
```

---

## 5. Product & Catalog APIs

### `POST /api/v1/products/`
- **Description**: Creates a product in the vendor's store.
- **Permissions**: IsStoreOwner.
- **Request Body**:
```json
{
  "name": "Honeycrisp Apple",
  "second_name": "Sweet Red Apple",
  "category_id": 1,
  "description": "Crisp and juicy sweet apples.",
  "measure": 1,
  "unit": "kg",
  "currency": "TK",
  "price": "220.00",
  "offer": true,
  "offered_discount": "10.00",
  "image": "<multipart-form-data>"
}
```

### `GET /api/v1/catalog/products/`
- **Description**: Customer product search across stores or filtered by store.
- **Permissions**: Public.
- **Query Parameters**:
  - `store_id` (int, optional)
  - `category_id` (int, optional)
  - `search` (string, optional): Searches name, second_name, tags, barcode, SKU
  - `page`, `page_size`

### `GET /products/api/barcode-lookup/`
- **Description**: Fast in-store shelf barcode scanning lookup. Resolves exact manufacturer EAN/UPC barcode or SKU within a specific store context with strict tenant isolation.
- **Permissions**: AllowAny (Public / In-store Walk-in Shoppers).
- **Query Parameters**:
  - `store_id` (int, required): Store being shopped.
  - `code` (string, required): Barcode string (e.g. `8901030383719`) or SKU code.
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Product found.",
  "data": {
    "id": 14,
    "name": "Crunchy Almond Cereal 500g",
    "second_name": "Almond Flakes",
    "barcode": "8901030383719",
    "sku": "SKU-ALMOND-500",
    "price": "60.00",
    "offered_price": "60.00",
    "is_in_stock": true,
    "available_quantity": "50.000"
  },
  "errors": null
}
```

---

## 6. Inventory & Purchasing APIs

### `GET /api/v1/inventory/balances/`
- **Description**: Current stock balance for all products in vendor's store.
- **Permissions**: IsStoreOwner.
- **Response Data Item**:
```json
{
  "product_id": 12,
  "product_name": "Honeycrisp Apple",
  "unit": "kg",
  "on_hand": "150.000",
  "reserved": "15.000",
  "available": "135.000",
  "low_stock_threshold": "20.000",
  "is_low_stock": false
}
```

### `POST /api/v1/purchases/receive/`
- **Description**: Receive purchased stock from a supplier into inventory.
- **Permissions**: IsStoreOwner.
- **Request Body**:
```json
{
  "supplier_id": 3,
  "items": [
    {
      "product_id": 12,
      "quantity": "50.000",
      "unit_cost": "180.00"
    }
  ],
  "notes": "Delivered via Supplier Truck #4"
}
```

---

## 7. Draft Memos & Shopping Cart APIs

### `GET /api/v1/memos/current/`
- **Description**: Returns the customer's active draft memo.
- **Permissions**: IsCustomer.

### `POST /api/v1/memos/current/items/`
- **Description**: Adds or updates an item in the current memo.
- **Permissions**: IsCustomer.
- **Request Body**:
```json
{
  "product_id": 12,
  "quantity": "2.5"
}
```

### `POST /cards/{id}/scan-add/`
- **Description**: Physical In-Store Barcode Scanner integration. Enables a customer walking inside a store to scan a product barcode or SKU off the shelf; automatically resolves the product in the store, validates stock, and either adds a new line item or increments quantity by specified amount (default `1.000`).
- **Permissions**: `IsAuthenticated` (Memo owner only).
- **Request Body**:
```json
{
  "code": "8901030383719",
  "quantity": "1.000"
}
```
- **Response** (`201 Created`):
```json
{
  "success": true,
  "message": "Scanned 'Crunchy Almond Cereal 500g' added to your shopping memo.",
  "data": {
    "id": 5,
    "store": 1,
    "user": 2,
    "shopping_mode": "walk_in",
    "total_price": "60.00",
    "items": [
      {
        "id": 9,
        "product": 14,
        "product_name": "Crunchy Almond Cereal 500g",
        "barcode": "8901030383719",
        "aisle": "Aisle 3 - Breakfast",
        "shelf_location": "Rack 2, Top",
        "is_picked": false,
        "picked_at": null,
        "quantity": "1.000",
        "price": "60.00",
        "total": "60.00"
      }
    ]
  },
  "errors": null
}
```

### `POST /cards/{id}/toggle-item-picked/`
- **Description**: Toggles or marks the physical in-store basket picking status of a specific line item in a shopping memo. Sets `picked_at` timestamp and dynamically recalculates card picking progress metrics (`total_items_count`, `picked_items_count`, `is_fully_picked`, `picking_progress_percent`).
- **Permissions**: `IsAuthenticated` (Memo owner only).
- **Request Body**:
```json
{
  "item_id": 9,
  "is_picked": true
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Item 'Crunchy Almond Cereal 500g' marked as picked.",
  "data": {
    "item": {
      "id": 9,
      "product": 14,
      "aisle": "Aisle 3 - Breakfast",
      "shelf_location": "Rack 2, Top",
      "is_picked": true,
      "picked_at": "2026-10-24T22:20:00Z",
      "quantity": "1.000",
      "subtotal": "60.00"
    },
    "total_items_count": 3,
    "picked_items_count": 2,
    "is_fully_picked": false,
    "picking_progress_percent": 66.7
  },
  "errors": null
}
```

### `POST /cards/{id}/batch-pick/`
- **Description**: Atomically marks multiple items in a shopping memo as physically picked or unpicked in one operation.
- **Permissions**: `IsAuthenticated` (Memo owner only).
- **Request Body**:
```json
{
  "item_ids": [9, 10, 11],
  "is_picked": true
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "3 item(s) updated in shopping basket.",
  "data": {
    "id": 5,
    "total_items_count": 3,
    "picked_items_count": 3,
    "is_fully_picked": true,
    "picking_progress_percent": 100.0,
    "items": [...]
  },
  "errors": null
}
```

### `GET /cards/{id}/?sort_by=aisle` & `GET /cards/active/?store_id=<id>&sort_by=aisle`
- **Description**: Walking Route Optimization. Sorts memo items by store physical layout (`product__aisle`, `product__shelf_location`, `id`) so in-store walk-in shoppers can walk through the physical aisles sequentially (e.g. Aisle 1 -> Aisle 2 -> Aisle 3) without backtracking.
- **Permissions**: `IsAuthenticated` (Customer owns memo).

### `PATCH /cards/{id}/set-budget/`
- **Description**: Sets, updates, or clears (`"budget_limit": null`) the shopping budget ceiling for the memo. Exposes computed fields `budget_remaining`, `is_over_budget`, and `budget_used_percent` on the card object.
- **Permissions**: `IsAuthenticated` (Customer owns memo).
- **Request Body**:
```json
{
  "budget_limit": "200.00"
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Budget limit set to 200.00.",
  "data": {
    "id": 5,
    "budget_limit": "200.00",
    "budget_remaining": "50.00",
    "is_over_budget": false,
    "budget_used_percent": 75.0,
    "total_price": "150.00"
  },
  "errors": null
}
```

### `POST /cards/{id}/compare-store/`
- **Description**: Cross-Store Shopping Memo Comparison. Compares all items in the customer's current memo against a target store's catalog. Matches items via Barcode -> SKU -> Case-insensitive name. Reports detailed price differences, potential savings at target store, missing unfulfillable products, and overall feasibility (`can_fulfill_all`).
- **Permissions**: `IsAuthenticated` (Customer owns memo).
- **Request Body**:
```json
{
  "target_store_id": 2
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Store comparison completed.",
  "data": {
    "source_store_id": 1,
    "source_store_name": "Apex Supermarket",
    "target_store_id": 2,
    "target_store_name": "Metro Mega Store",
    "can_fulfill_all": true,
    "total_items_in_memo": 2,
    "matched_items_count": 2,
    "missing_items_count": 0,
    "source_total_price": "85.00",
    "target_total_price": "75.00",
    "potential_savings_at_target": "10.00",
    "items": [
      {
        "source_item_id": 9,
        "source_product_id": 14,
        "source_product_name": "Full Cream Milk 1L",
        "quantity": "2.000",
        "source_unit_price": "25.00",
        "source_line_total": "50.00",
        "status": "available",
        "target_product_id": 31,
        "target_product_name": "Full Cream Milk 1L",
        "target_unit_price": "20.00",
        "target_line_total": "40.00",
        "price_difference": "-10.00",
        "match_type": "barcode"
      }
    ],
    "missing_items": []
  },
  "errors": null
}
```

### `POST /cards/{id}/transfer-store/`
- **Description**: Store Memo Transfer. Transfers the customer's shopping memo items from the source store to a target store's catalog. Automatically matches products (Barcode -> SKU -> Name), re-prices items at target store prices, updates `card.store` and `card.vendor`, and disconnects store-specific coupons.
- **Permissions**: `IsAuthenticated` (Customer owns memo).
- **Request Body**:
```json
{
  "target_store_id": 2,
  "omit_missing": true,
  "clone": false
}
```
- **Response** (`200 OK` or `201 Created` if `clone=true`):
```json
{
  "success": true,
  "message": "Memo transferred to Metro Mega Store.",
  "data": {
    "id": 5,
    "store": 2,
    "vendor": 4,
    "shopping_mode": "walk_in",
    "total_price": "75.00",
    "items": [...]
  },
  "errors": null
}
```

---

## 8. Orders & Fulfillment APIs

### `POST /orders/submit/`
- **Description**: Submits the draft memo into a confirmed customer order. Atomically reserves stock.
- **Permissions**: `IsAuthenticated`.
- **Request Body**:
```json
{
  "card_id": 5,
  "fulfillment_type": "delivery",
  "delivery_address": "House 5, Road 2, Sector 4, Uttara, Dhaka",
  "notes": "Ring doorbell twice please.",
  "idempotency_key": "c3f8d7b2-8419-4b2a-a991-3818e5e69bf1"
}
```

### `POST /orders/{id}/accept/`
- **Description**: Vendor accepts the submitted customer order. Stamps `accepted_at`.
- **Permissions**: `IsAuthenticated` (Store Vendor only).

### `POST /orders/{id}/prepare/`
- **Description**: Vendor moves accepted order into preparation status. Stamps `preparing_at`.
- **Permissions**: `IsAuthenticated` (Store Vendor only).

### `POST /orders/{id}/dispatch/`
- **Description**: Vendor marks order as `ready_for_pickup` (if pickup) or `out_for_delivery` (if delivery). Stamps `dispatched_at` and notifies customer.
- **Permissions**: `IsAuthenticated` (Store Vendor only).

### `POST /orders/{id}/fulfill/`
- **Description**: Marks order as completed. Deducts reserved stock from inventory ledger, stamps `completed_at`, marks payment collected if requested, and issues immutable `SalesMemo`.
- **Permissions**: `IsAuthenticated` (Store Vendor only).
- **Request Body**:
```json
{
  "payment_collected": true
}
```

### `POST /orders/{id}/cancel/`
- **Description**: Cancels order and atomically returns reserved inventory back to available stock. Customers can only cancel while order is in `submitted` or `accepted` status before preparation begins. Vendors can reject/cancel at any pre-completion stage.
- **Permissions**: `IsAuthenticated` (Order Customer or Store Vendor).

### `POST /orders/{id}/assign-delivery/`
- **Description**: Vendor assigns delivery driver/personnel details (`driver_name`, `driver_phone`, `vehicle_type`, `tracking_notes`, `estimated_delivery_time`, `auto_dispatch`) to an active home delivery order. When `auto_dispatch=True`, advances order status to `out_for_delivery` and notifies customer with driver contact info.
- **Permissions**: `IsAuthenticated` (Store Vendor only).
- **Request Body**:
```json
{
  "driver_name": "Tariqul Islam",
  "driver_phone": "+8801812345678",
  "vehicle_type": "Motorbike",
  "tracking_notes": "Carrying insulated bag #12",
  "estimated_delivery_time": "2026-10-24T17:30:00Z",
  "auto_dispatch": true
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Delivery driver assigned successfully.",
  "data": {
    "id": 1,
    "status": "out_for_delivery",
    "delivery_person_name": "Tariqul Islam",
    "delivery_person_phone": "+8801812345678",
    "delivery_vehicle_type": "Motorbike",
    "delivery_tracking_notes": "Carrying insulated bag #12",
    "delivery_assigned_at": "2026-10-24T16:10:00Z",
    "estimated_delivery_time": "2026-10-24T17:30:00Z",
    "dispatched_at": "2026-10-24T16:10:00Z"
  },
  "errors": null
}
```

### `POST /orders/{id}/handover/`
- **Description**: Store owner/staff collects products picked by a walk-in customer (or ready for pickup) and hands them over directly at the counter, collects payment on the spot, atomically fulfills reserved stock, and generates finalized `SalesMemo`.
- **Permissions**: `IsAuthenticated` (Store Vendor only).
- **Request Body**:
```json
{
  "payment_collected": true
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Order handed over to customer successfully and sales memo issued.",
  "data": {
    "id": 1,
    "status": "completed",
    "payment_status": "collected",
    "fulfillment_type": "walk_in",
    "completed_at": "2026-10-24T17:15:00Z",
    "paid_at": "2026-10-24T17:15:00Z"
  },
  "errors": null
}
```

### `POST /orders/counter-lookup/`
- **Description**: In-store Counter POS verification. Store owner or counter staff types or scans the customer's 6-digit walk-in / pickup verification code (`walk_in_code`) to instantly retrieve order items and details for verification, item picking, and handover.
- **Permissions**: `IsAuthenticated` (Store Vendor or Platform Staff only; strictly scoped to the store's vendor).
- **Request Body**:
```json
{
  "code": "481923",
  "store_id": 1
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Counter walk-in order retrieved.",
  "data": {
    "id": 12,
    "order_number": "ORD-6F9812A9",
    "customer": 5,
    "customer_email": "shopper@test.com",
    "vendor": 2,
    "vendor_email": "vendor@test.com",
    "store": 1,
    "store_name": "City Mart",
    "status": "submitted",
    "fulfillment_type": "walk_in",
    "walk_in_code": "481923",
    "delivery_address": "",
    "delivery_fee": "0.00",
    "subtotal": "500.00",
    "total_amount": "500.00",
    "payment_method": "cod",
    "payment_status": "pending",
    "items": [
      {
        "id": 24,
        "product": 8,
        "product_name_snapshot": "Organic Honey 500g",
        "unit_price_snapshot": "250.00",
        "quantity": "2.000",
        "line_total": "500.00"
      }
    ]
  },
  "errors": null
}
```

### `GET /orders/{id}/sales_memo/`
- **Description**: Download or view finalized immutable sales memo receipt. Contains itemized breakdown, discounts, totals, `walk_in_code_snapshot`, and monospace `thermal_receipt`. Passing `?receipt_format=thermal` returns raw plain-text formatted slip.
- **Permissions**: `IsAuthenticated` (Order Customer or Store Vendor).
- **Query Parameters**:
  - `receipt_format`: Set to `thermal` or `text` to receive direct plain text 40-col slip.

### `GET /orders/{id}/thermal-receipt/`
- **Description**: Direct endpoint returning standard 40-column monospace thermal receipt slip (`text/plain; charset=utf-8`) ready for 58mm / 80mm Bluetooth / USB POS printers or terminal display.
- **Permissions**: `IsAuthenticated` (Order Customer or Store Vendor).

### `GET /orders/sales-memos/`
- **Description**: Digital Sales Memo History / Receipt Wallet. Enables customers to browse, filter, search, and paginate through all finalized digital sales receipts across all visited stores. Vendors can list sales memos for their store(s) with `?as_vendor=true`.
- **Permissions**: `IsAuthenticated` (Customer sees their own memos; Vendor sees their store memos; Staff/Superuser sees all).
- **Query Parameters**:
  - `store_id`: Filter memos by a specific store ID.
  - `from_date`: Filter memos on or after timestamp (ISO format).
  - `to_date`: Filter memos on or before timestamp (ISO format).
  - `search`: Search query matching memo number, order number, store name, or walk-in code.
  - `as_vendor`: If `true`, queries from store vendor perspective instead of customer perspective.
  - `page`, `page_size`: Standard collection pagination.

### `GET /orders/customer-spending/`
- **Description**: Multi-store customer spending analytics. Computes server-side SQL database aggregations of the authenticated customer's total expenditure, total savings, total visited stores, and detailed store-by-store breakdown.
- **Permissions**: `IsAuthenticated` (strictly scoped to `request.user`).
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Customer multi-store spending analytics retrieved.",
  "data": {
    "total_spent": "1590.00",
    "total_saved": "50.00",
    "total_memos": 3,
    "stores_visited_count": 2,
    "store_breakdown": [
      {
        "store_id": 1,
        "store_name": "Green Valley Grocery",
        "memo_count": 2,
        "total_spent": "1350.00",
        "last_visit": "2026-10-24T18:30:00Z"
      },
      {
        "store_id": 2,
        "store_name": "Sunrise Bakery",
        "memo_count": 1,
        "total_spent": "240.00",
        "last_visit": "2026-10-24T19:00:00Z"
      }
    ]
  },
  "errors": null
### `GET /orders/{id}/qr-code/`
- **Description**: Generates and serves a vector SVG QR code representation of the order verification data (`walk_in_code`, `order_number`, `store_id`). Enables physical in-store walk-in customers to display an interactive SVG QR code on their smartphone screen for 1-second optical scanning by the counter POS barcode scanner or mobile cashier camera.
- **Permissions**: `IsAuthenticated` (Order owner or Store vendor only).
- **Response** (`200 OK`, `Content-Type: image/svg+xml`):
```xml
<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 37 37">
  ...
</svg>
```
*Note: The standalone Base64/UTF-8 data URI is also exposed automatically on every order detail via the `qr_code_data_uri` field in `OrderSerializer` (`data:image/svg+xml;utf8,<svg...`).*

### `POST /orders/{id}/reorder/`
- **Description**: Quick 1-Tap Reorder. Clones all items from a past completed/delivered order directly into a new active draft shopping memo for that same store. Automatically re-validates current product availability, verifies the store is still active, recalculates authoritative current pricing, and populates the memo items.
- **Permissions**: `IsAuthenticated` (Customer who owns the past order).
- **Response** (`201 Created`):
```json
{
  "success": true,
  "message": "Shopping memo for 'Green Valley Grocery' populated from order ORD-B4F238.",
  "data": {
    "id": 14,
    "user": 5,
    "store": 1,
    "shopping_mode": "online",
    "status": "draft",
    "total_price": "240.00",
    "items": [
      {
        "id": 22,
        "product": 8,
        "product_name": "Organic Honey 500g",
        "quantity": "2.000",
        "price": "120.00",
        "total": "240.00"
      }
    ]
  },
  "errors": null
}
```

---

## 9. Purchases & Supplier Management APIs

### `POST /purchases/suppliers/`
- **Description**: Register a new supplier scoped to a vendor's store.
- **Permissions**: IsAuthenticated & IsVendor.
- **Request Body**:
```json
{
  "store": 1,
  "name": "Fresh Farms Ltd",
  "contact_person": "Karim Ullah",
  "email": "karim@freshfarms.com",
  "phone": "+8801700000000",
  "address": "Savar, Dhaka"
}
```

### `POST /purchases/orders/`
- **Description**: Create a draft purchase order. Does NOT impact inventory.
- **Permissions**: IsAuthenticated & IsVendor.
- **Request Body**:
```json
{
  "store_id": 1,
  "supplier_id": 1,
  "reference": "SUP-INV-2026-001",
  "additional_charges": "50.00",
  "items": [
    {
      "product_id": 5,
      "quantity": "100.000",
      "unit_cost": "45.00"
    }
  ]
}
```

### `POST /purchases/orders/{id}/receive/`
- **Description**: Confirms arrival of purchased goods. Atomically credits on-hand stock and writes immutable audit ledger entries.
- **Permissions**: IsAuthenticated & IsVendor (Store Owner).
- **Idempotency**: Cannot be called twice on the same purchase order.

---

## 10. Reporting & Analytics APIs

### `GET /reports/sales/`
- **Description**: Aggregates sales metrics (gross sales, net product sales, delivery fee total, completed order count, cancelled order count, COD collected vs outstanding).
- **Permissions**: IsAuthenticated & IsVendor.
- **Query Parameters**:
  - `store_id` (int, required)
  - `start_date` (YYYY-MM-DD, optional)
  - `end_date` (YYYY-MM-DD, optional)

### `GET /reports/inventory/`
- **Description**: Aggregates stock health, tracking counts, out-of-stock items, and low-stock alert thresholds.
- **Permissions**: IsAuthenticated & IsVendor.
- **Query Parameters**:
  - `store_id` (int, required)

### `GET /reports/purchases/`
- **Description**: Aggregates procurement spending, received PO totals, and purchase order counts.
- **Permissions**: IsAuthenticated & IsVendor.
- **Query Parameters**:
  - `store_id` (int, required)
  - `start_date` (YYYY-MM-DD, optional)
  - `end_date` (YYYY-MM-DD, optional)

---

## 11. Geospatial Nearby Discovery & Customer Favorites

### `GET /stores/nearby/`
- **Description**: Location-based discovery of active stores. Calculates Haversine distance, filters within radius, and orders results by ascending distance.
- **Permissions**: Public (`AllowAny`).
- **Query Parameters**:
  - `lat` (float, -90.0 to 90.0, optional)
  - `lng` (float, -180.0 to 180.0, optional)
  - `radius_km` (float, 0.1 to 100.0, default: `10.0`)
- **Fallback**: When `lat` or `lng` are omitted, gracefully returns active stores without distance calculation.
- **Response**: Paginated list of stores including `distance_km` and `is_favorite` boolean for authenticated customers.

### `POST /stores/{id}/favorite/`
- **Description**: Idempotently adds a store to authenticated customer's favorites.
- **Permissions**: `IsAuthenticated` & `IsCustomer`.
- **Response**: `201 Created` with saved `FavoriteStore` record.

### `DELETE /stores/{id}/favorite/` (or `POST /stores/{id}/unfavorite/`)
- **Description**: Removes store from authenticated customer's favorites.
- **Permissions**: `IsAuthenticated` & `IsCustomer`.
- **Response**: `200 OK`.

### `GET /stores/favorites/`
- **Description**: Lists authenticated customer's saved stores with pagination and store details. Enforces customer isolation.
- **Permissions**: `IsAuthenticated` & `IsCustomer`.

---

## 12. Draft Shopping Memo (Card) APIs

### `GET /cards/active/`
- **Description**: Returns or auto-initializes the authenticated customer's current active draft shopping memo. Supports `store_id` to retrieve or initialize a draft memo specifically for that store, and `shopping_mode` (`walk_in` for in-store shopping, or `remote` for home ordering).
- **Permissions**: `IsAuthenticated`.
- **Query Parameters**:
  - `store_id` (int, optional): Store ID to scope draft memo.
  - `shopping_mode` (string, optional): `'walk_in'` or `'remote'`.
- **Response**: `200 OK` with `Card` object containing `items`, `store`, `store_name`, `shopping_mode`, and `total_price`.

### `POST /stores/{id}/memo/`
- **Description**: Convenient store-entry action. Retrieves or auto-initializes the customer's draft memo specifically for the entered store.
- **Permissions**: `IsAuthenticated`.
- **Request Body (optional)**:
```json
{
  "shopping_mode": "walk_in"
}
```

### `GET /cards/`
- **Description**: Lists all active and saved shopping memos for the customer.
- **Query Parameters**:
  - `store_id` (int, optional): Filter memos for a specific store.
  - `is_completed` (bool, optional): Filter by completion status (`false` for drafts).

### `POST /cards/{id}/add-item/`
- **Description**: Adds a product to draft memo. Enforces single-store rule and zero premature stock movement.
- **Permissions**: `IsAuthenticated` (Card owner only).
- **Request Body**:
```json
{
  "product_id": 12,
  "quantity": "2.000"
}
```

### `POST /cards/{id}/update-item/`
- **Description**: Updates the quantity of an item within the draft memo and refreshes with current effective price.
- **Permissions**: `IsAuthenticated` (Card owner only).
- **Request Body**:
```json
{
  "item_id": 4,
  "quantity": "3.000"
}
```

### `POST /cards/{id}/remove-item/`
- **Description**: Removes an item from the draft memo. If memo becomes empty, automatically unbinds the store context so customer can pick from another store.
- **Permissions**: `IsAuthenticated` (Card owner only).
- **Request Body**:
```json
{
  "item_id": 4
}
```

### `POST /cards/{id}/clear/`
- **Description**: Empties all items from the draft memo and unbinds store.
- **Permissions**: `IsAuthenticated` (Card owner only).

### `POST /cards/{id}/checkout/`
- **Description**: Converts customer's draft shopping memo card into a submitted order with atomic inventory reservation and catalog price/offer revalidation. Supports `fulfillment_type="walk_in"` (for in-store shopping with zero delivery fee and no address required), `"pickup"`, or `"delivery"`.
- **Permissions**: `IsAuthenticated` (Card owner only).
- **Request Body**:
```json
{
  "fulfillment_type": "walk_in",
  "notes": "Self-picked items from aisle 3",
  "idempotency_key": "chk-98a0f2b3"
}
```
- **Response**: `201 Created` with snapshot `Order` object.

### `GET /cards/saved/`
- **Description**: Returns all saved "buy next time" planning memos for the authenticated customer, optionally filtered by `store_id`.
- **Permissions**: `IsAuthenticated`.
- **Query Parameters**:
  - `store_id` (int, optional): Scopes the listing to a specific store.
- **Response**: Array of saved `Card` objects with `is_saved_for_later: true` and `planned_visit_date`.

### `POST /cards/create-saved/`
- **Description**: Directly creates a new named planning memo for a store with a future planned visit date.
- **Permissions**: `IsAuthenticated`.
- **Request Body**:
```json
{
  "store_id": 1,
  "title": "Weekend Home Renovation Supplies",
  "planned_visit_date": "2026-11-05",
  "notes": "Pick up hammer and 2 boxes of steel nails at aisle 4",
  "shopping_mode": "walk_in"
}
```
- **Response**: `201 Created` with `Card` object.

### `POST /cards/{id}/save-for-later/`
- **Description**: Converts an active shopping memo into a saved planning list for a future visit.
- **Permissions**: `IsAuthenticated` (Card owner only).
- **Request Body**:
```json
{
  "title": "Deferred Tool Shopping",
  "planned_visit_date": "2026-11-10"
}
```
- **Response**: `200 OK` with updated `Card` object (`is_saved_for_later: true`).

### `POST /cards/{id}/activate/`
- **Description**: Activates a saved planning memo as the current active shopping cart for that store. If an active cart already exists, safely swaps the previous active cart to saved status (`strategy="swap"`) or merges items (`strategy="merge"`).
- **Permissions**: `IsAuthenticated` (Card owner only).
- **Request Body**:
```json
{
  "strategy": "swap"
}
```
- **Response**: `200 OK` with activated `Card` object (`is_saved_for_later: false`).

### `POST /cards/{id}/duplicate/`
- **Description**: Duplicates a memo and all its item snapshots into an independent saved or active memo.
- **Permissions**: `IsAuthenticated` (Card owner only).
- **Request Body**:
```json
{
  "title": "Duplicated Tool List",
  "as_saved": true
}
```
- **Response**: `201 Created` with duplicated `Card` object.

---

## 13. Notifications & Alerting APIs

### `GET /notifications/`
- **Description**: Returns the paginated notification feed for the authenticated user.
- **Permissions**: `IsAuthenticated`.
- **Query Parameters**:
  - `unread_only` (bool, optional, e.g. `?unread_only=true`): Filter to show unread notifications only.
- **Response**: Paginated array of notifications (`id`, `notification_type`, `title`, `message`, `is_read`, `read_at`, `store_id`, `store_name`, `created_at`).

### `GET /notifications/unread-count/`
- **Description**: Lightweight endpoint returning the number of unread notifications for notification badge counters.
- **Permissions**: `IsAuthenticated`.
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Unread notification count retrieved.",
  "data": {
    "unread_count": 3
  },
  "errors": null
}
```

### `PATCH /notifications/{id}/read/` (or `POST /notifications/{id}/read/`)
- **Description**: Marks a specific notification as read.
- **Permissions**: `IsAuthenticated` (Must be the notification recipient).
- **Response**: `200 OK` with updated notification.

### `POST /notifications/mark-all-read/`
- **Description**: Bulk marks all unread notifications as read for the authenticated user.
- **Permissions**: `IsAuthenticated`.
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Marked 5 notifications as read.",
  "data": {
    "marked_count": 5
  },
  "errors": null
}
```

---

## 14. Delivery & Payment Decoupling

### `POST /orders/{id}/collect-payment/`
- **Description**: Collects cash payment on Cash On Delivery (COD) or in-store pickup orders without entangling fulfillment state. Records timestamp `paid_at` and records the collecting staff/vendor `payment_collected_by`.
- **Permissions**: `IsAuthenticated` & `IsStoreOwner` (Only the store vendor or superuser can collect payment).
- **Request Body**: Empty or optional notes.
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Payment collected successfully.",
  "data": {
    "order": {
      "id": 14,
      "order_number": "ORD-20261024-XXXX",
      "payment_status": "PAID",
      "paid_at": "2026-10-24T01:40:00Z",
      "status": "ACCEPTED"
    }
  },
  "errors": null
}
```

---

## 15. Tenant-Safe Caching & O(1) Invalidation

### Caching Architecture
- **Tenant Isolation**: Keys incorporate store ID and tenant version: `smartmemo:store:{store_id}:{namespace}:v{version}:{identifier}:{param_hash}`.
- **O(1) Namespace Invalidation**: When a store profile, category, or product is modified, the store namespace version is atomically incremented (`CacheService.invalidate_catalog(store_id)`). Stale keys expire automatically in $O(1)$ time without scanning or flushing Redis.
- **Fail-Safe Operation**: All cache calls are wrapped in exception handlers. In the event of Redis downtime, requests bypass cache and query PostgreSQL directly without error.
- **Authoritative Checkout**: Order creation, inventory reservation, and payment collection strictly bypass cache and lock database rows via `select_for_update()`.

---

## 16. Deployment Observability & Health Probes

### `GET /health/`
- **Description**: Returns HTML server health dashboard by default. If `Accept: application/json` or `?format=json` is provided, returns JSON system performance metrics (CPU count, memory usage, load averages, disk space).
- **Permissions**: Public (`AllowAny`).

### `GET /health/live/`
- **Description**: Container liveness probe. Verifies process is alive and receiving HTTP requests.
- **Permissions**: Public (`AllowAny`).
- **Response** (`200 OK`):
```json
{
  "status": "alive",
  "service": "smart-memo-backend"
}
```

### `GET /health/ready/`
- **Description**: Deep readiness probe. Verifies PostgreSQL connectivity (`SELECT 1`), unapplied database migrations (`MigrationExecutor`), and cache availability.
- **Permissions**: Public (`AllowAny`).
- **Response** (`200 OK` when healthy):
```json
{
  "status": "ready",
  "service": "smart-memo-backend",
  "checks": {
    "database": "connected",
    "migrations": "up_to_date",
    "cache": "connected"
  }
}
```
- **Response** (`503 Service Unavailable` on database/migration failure):
```json
{
  "status": "unhealthy",
  "service": "smart-memo-backend",
  "checks": {
    "database": "unhealthy: OperationalError",
    "migrations": "up_to_date",
    "cache": "connected"
  }
}
```

---

## 14. Audit Logging & Activity Trail APIs

### `GET /audit/logs/`
- **Description**: Read-only listing of tenant-isolated immutable audit logs.
  - Staff / Admin: Views platform-wide audit entries or filters by `store_id`.
  - Vendor: Automatically filtered strictly to audit entries for vendor-owned stores.
  - Customer / Anonymous: Access denied (`403 Forbidden` / `401 Unauthorized`).
- **Permissions**: `IsAuthenticated` (with role checks).
- **Query Parameters**:
  - `action`: Filter by action identifier (`STORE_VERIFIED`, `STORE_SUSPENDED`, `STORE_ACTIVATED`, `INVENTORY_ADJUSTED`, `ORDER_CANCELLED`, `ORDER_PAYMENT_COLLECTED`, `PASSWORD_CHANGED`).
  - `target_model`: Filter by model name (`Store`, `StockBalance`, `Order`, `User`).
  - `target_id`: Filter by model record ID.
  - `store_id`: Filter by specific store ID (validated against vendor ownership).
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Data retrieved successfully",
  "data": [
    {
      "id": 104,
      "store": 1,
      "store_name": "Fresh Mart",
      "actor": 5,
      "actor_email": "vendor@example.com",
      "actor_role": "vendor",
      "action": "INVENTORY_ADJUSTED",
      "target_model": "StockBalance",
      "target_id": "42",
      "ip_address": "127.0.0.1",
      "user_agent": "Mozilla/5.0",
      "details": {
        "product_id": "15",
        "adjustment_qty": "10.000",
        "previous_on_hand": "40.000",
        "new_on_hand": "50.000",
        "movement_type": "manual_adjustment",
        "notes": "Physical inventory recount found extra stock"
      },
      "created_at": "2026-10-24T09:01:00Z"
    }
  ],
  "pagination": {
    "count": 1,
    "total_pages": 1,
    "current_page": 1,
    "page_size": 10,
    "next": null,
    "previous": null,
    "has_next": false,
    "has_previous": false
  },
  "errors": null
}
```

### `GET /audit/logs/{id}/`
- **Description**: Detailed retrieval of a single audit log entry.
- **Permissions**: `IsAuthenticated` (enforces vendor store ownership or staff role).
- **Security**: Direct mutations (`POST`, `PUT`, `PATCH`, `DELETE`) are strictly rejected with `405 Method Not Allowed`. Audit log models disallow updates and deletions at ORM level (`PermissionDenied`).

---

## 15. Customer Saved Delivery Addresses & Dynamic Delivery Fees

### `GET /users/addresses/`
- **Description**: List all saved delivery addresses for the authenticated customer. Soft-deleted records are automatically excluded.
- **Permissions**: `IsAuthenticated` (Customer).
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Delivery addresses retrieved successfully.",
  "data": [
    {
      "id": 12,
      "label": "Home",
      "recipient_name": "Alice Smith",
      "phone_number": "+8801700000001",
      "address_line": "House 12, Road 5, Block B",
      "city": "Dhaka",
      "postal_code": "1212",
      "latitude": 23.815,
      "longitude": 90.415,
      "delivery_instructions": "Leave with gate security",
      "is_default": true,
      "created_at": "2026-10-24T09:15:00Z"
    }
  ]
}
```

### `POST /users/addresses/`
- **Description**: Create a new delivery address for the authenticated customer. First address created automatically becomes the default. If `is_default=True` is passed, existing defaults for this customer are atomically reset.
- **Permissions**: `IsAuthenticated` (Customer).
- **Request Body**:
```json
{
  "label": "Office",
  "recipient_name": "Alice Smith",
  "phone_number": "+8801700000002",
  "address_line": "Level 8, Tech Tower, Banani",
  "city": "Dhaka",
  "postal_code": "1213",
  "latitude": 23.7937,
  "longitude": 90.4066,
  "delivery_instructions": "Call upon arrival",
  "is_default": false
}
```

### `GET /users/addresses/{id}/`
- **Description**: Retrieve a specific saved address by ID. Enforces strict customer ownership; attempts by other users return `404 Not Found`.

### `PATCH /users/addresses/{id}/`
- **Description**: Update fields of a saved address. Validates latitude/longitude bounds if provided.

### `DELETE /users/addresses/{id}/`
- **Description**: Soft-deletes a saved address (`is_deleted=True`), preserving historical order snapshots while removing it from customer view.

### `POST /users/addresses/{id}/set-default/`
- **Description**: Marks the specified address as default and atomically unsets default status on all other addresses owned by the customer.

### `POST /stores/{id}/calculate-delivery-fee/`
- **Description**: Real-time delivery quote calculating distance and tiered delivery fee from the store to the customer's coordinates or saved `address_id`.
- **Permissions**: Public (`AllowAny`).
- **Request Body (Coordinates or Address ID)**:
```json
{
  "lat": 23.7500,
  "lng": 90.4125
}
```
*or*
```json
{
  "address_id": 12
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Delivery fee calculated successfully.",
  "data": {
    "store_id": 1,
    "distance_km": 6.71,
    "delivery_fee": "100.65",
    "is_dynamic": true
  }
}
```
*(Tiered fee rule: store's base `delivery_fee` covers up to 2.0 km. Beyond 2.0 km, additional distance is billed at 15.00/km).*

### Memo Checkout with Address Support
- **Endpoint**: `POST /cards/{id}/checkout/`
- **Payload**: Accepts `"address_id": 12` (or falls back to customer's default address or profile).
- **Behavior**: Snapshots recipient, formatted address, phone, and delivery instructions directly onto the `Order`, and calculates distance-based dynamic delivery fee.

---

## 16. Physical Inventory Audit & Batch Stock Reconciliation APIs

### `GET /inventory/reconciliations/`
- **Description**: List all inventory count and reconciliation sessions for the vendor's stores.
- **Permissions**: `IsAuthenticated`, `IsVendor`.
- **Query Parameters**:
  - `store_id`: Filter sessions by store (must be owned by the vendor).

### `POST /inventory/reconciliations/`
- **Description**: Create a draft physical inventory count session. Snapshots current system stock for each item, compares against counted physical stock, and calculates quantity discrepancy and monetary variance.
- **Permissions**: `IsAuthenticated`, `IsVendor`.
- **Request Body**:
```json
{
  "store_id": 1,
  "notes": "Month-end audit for beverage section",
  "items": [
    {
      "product_id": 10,
      "physical_stock": "45.000",
      "notes": "5 cans damaged"
    },
    {
      "product_id": 12,
      "physical_stock": "35.000",
      "notes": "5 extra bottles found in backroom"
    }
  ]
}
```
- **Response** (`201 Created`):
```json
{
  "success": true,
  "message": "Stock reconciliation draft created successfully.",
  "data": {
    "id": 5,
    "store": 1,
    "store_name": "Fresh Mart",
    "reconciliation_number": "REC-1-A1B2C3D4",
    "status": "draft",
    "notes": "Month-end audit for beverage section",
    "total_items_counted": 2,
    "total_discrepancy_qty": "0.000",
    "total_discrepancy_value": "-350.00",
    "applied_at": null,
    "applied_by_email": null,
    "initiated_by_email": "vendor@example.com",
    "items": [
      {
        "id": 15,
        "product": 10,
        "product_name": "Orange Juice 1L",
        "system_stock": "50.000",
        "physical_stock": "45.000",
        "discrepancy": "-5.000",
        "unit_cost_snapshot": "120.00",
        "variance_value": "-600.00",
        "notes": "5 cans damaged"
      }
    ]
  }
}
```

### `GET /inventory/reconciliations/{id}/`
- **Description**: Detailed retrieval of a reconciliation session including all counted item discrepancies and variance breakdowns.
- **Permissions**: `IsAuthenticated`, `IsVendor` (strictly scoped to store owner).

### `POST /inventory/reconciliations/{id}/apply/`
- **Description**: Atomically commit count variances into inventory balances.
  - Acquires row locks (`select_for_update`) on affected `StockBalance` records.
  - Enforces invariant: `new_on_hand` cannot drop below `balance.reserved` (prevents overselling active orders).
  - Updates `balance.on_hand` and `product.stock`.
  - Logs `StockMovementType.RECONCILIATION` entries in the append-only `StockLedgerEntry` table.
  - Records an immutable `AuditLog` entry (`AuditAction.INVENTORY_RECONCILED`).
  - Invalidates store catalog cache.
  - Sets session status to `applied`.
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Stock reconciliation applied successfully to ledger.",
  "data": {
    "id": 5,
    "status": "applied",
    "applied_at": "2026-10-24T09:32:00Z",
    "applied_by_email": "vendor@example.com"
  }
}
```

### `POST /inventory/reconciliations/{id}/cancel/`
- **Description**: Cancels a draft reconciliation session without modifying inventory balances or ledger.
- **Permissions**: `IsAuthenticated`, `IsVendor`.

---

## 17. Verified Customer Store Reviews & Ratings APIs

### `GET /stores/{id}/reviews/`
- **Description**: Public endpoint to list all customer reviews for a given store, including ratings, comments, verified buyer order IDs, and vendor replies.
- **Permissions**: AllowAny (Public).
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Store reviews retrieved successfully.",
  "data": [
    {
      "id": 1,
      "store": 3,
      "store_name": "Organic Greens",
      "customer_email": "customer@example.com",
      "order": 14,
      "rating": 5,
      "comment": "Outstanding produce quality and super fast delivery!",
      "vendor_reply": "Thank you so much! We look forward to serving you again.",
      "vendor_replied_at": "2026-10-24T09:40:00Z",
      "created_at": "2026-10-24T09:35:00Z",
      "updated_at": "2026-10-24T09:40:00Z"
    }
  ]
}
```

### `POST /stores/{id}/reviews/`
- **Description**: Submit a verified customer review for a store. Enforces that the customer must have at least one `COMPLETED` order from this store (`verified purchase`), and enforces single-review anti-spam invariant (`unique_together = ('store', 'customer')`). Automatically synchronizes store's `average_rating` and `total_reviews` via SQL aggregations, and invalidates cached store profiles.
- **Permissions**: `IsAuthenticated` (Customer role).
- **Request Body**:
```json
{
  "rating": 5,
  "comment": "Outstanding produce quality and super fast delivery!",
  "order_id": 14
}
```
*(Note: `order_id` is optional; if omitted, the system links to the customer's most recent completed order at this store).*
- **Response** (`201 Created`):
```json
{
  "success": true,
  "message": "Review submitted successfully.",
  "data": {
    "id": 1,
    "store": 3,
    "rating": 5,
    "comment": "Outstanding produce quality and super fast delivery!",
    "created_at": "2026-10-24T09:35:00Z"
  }
}
```

### `POST /stores/reviews/{id}/reply/`
- **Description**: Store owner submits an official response to a customer review.
- **Permissions**: `IsAuthenticated` (Store Owner vendor only).
- **Request Body**:
```json
{
  "reply": "Thank you so much! We look forward to serving you again."
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Reply posted successfully.",
  "data": {
    "id": 1,
    "vendor_reply": "Thank you so much! We look forward to serving you again.",
    "vendor_replied_at": "2026-10-24T09:40:00Z"
  }
}
```

### `DELETE /stores/reviews/{id}/`
- **Description**: Delete a review. Customers can delete their own reviews; platform Staff/Admin can delete any review for moderation. Automatically recalculates store's `average_rating` and `total_reviews` and invalidates store cache.
- **Permissions**: `IsAuthenticated` (Review Author or Staff/Admin).
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Review deleted successfully.",
  "data": null
}
```

---

## 18. Store Promotional Coupons & Order Discounts APIs

### `GET /stores/{id}/coupons/`
- **Description**: Vendor retrieves all promotional coupons created for their store.
- **Permissions**: `IsAuthenticated`, `IsVendor` (Store Owner only).
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Coupons retrieved successfully.",
  "data": [
    {
      "id": 1,
      "store": 5,
      "store_name": "Organic Greens",
      "code": "SAVE20",
      "discount_type": "percentage",
      "discount_value": "20.00",
      "max_discount_amount": "50.00",
      "min_order_amount": "100.00",
      "max_uses": 200,
      "used_count": 14,
      "max_uses_per_customer": 1,
      "start_date": "2026-10-01T00:00:00Z",
      "end_date": "2026-11-01T00:00:00Z",
      "is_active": true
    }
  ]
}
```

### `POST /stores/{id}/coupons/`
- **Description**: Vendor creates a new promotional discount coupon scoped to their store.
- **Permissions**: `IsAuthenticated`, `IsVendor` (Store Owner only).
- **Request Body**:
```json
{
  "code": "SAVE20",
  "discount_type": "percentage",
  "discount_value": "20.00",
  "max_discount_amount": "50.00",
  "min_order_amount": "100.00",
  "max_uses": 200,
  "max_uses_per_customer": 1,
  "start_date": "2026-10-01T00:00:00Z",
  "end_date": "2026-11-01T00:00:00Z",
  "is_active": true
}
```
- **Response** (`201 Created`):
```json
{
  "success": true,
  "message": "Coupon 'SAVE20' created successfully.",
  "data": {
    "id": 1,
    "code": "SAVE20",
    "discount_type": "percentage",
    "discount_value": "20.00",
    "is_active": true
  }
}
```

### `GET /stores/coupons/{id}/`
- **Description**: Vendor views details of a specific coupon.
- **Permissions**: `IsAuthenticated`, `IsVendor` (Store Owner only).

### `PATCH /stores/coupons/{id}/`
- **Description**: Vendor updates coupon parameters (dates, active toggle, usage limits, discount values).
- **Permissions**: `IsAuthenticated`, `IsVendor` (Store Owner only).

### `DELETE /stores/coupons/{id}/`
- **Description**: Vendor deletes a coupon.
- **Permissions**: `IsAuthenticated`, `IsVendor` (Store Owner only).

### `GET /stores/coupons/{id}/usages/`
- **Description**: Vendor reviews the redemption ledger for a coupon, seeing which customers and orders used it and the exact discount amount applied.
- **Permissions**: `IsAuthenticated`, `IsVendor` (Store Owner only).

### `POST /cards/{id}/apply-coupon/`
- **Description**: Customer applies a store coupon code to their draft shopping memo card. Validates that the coupon belongs to the card's store, is active, within valid dates, satisfies `min_order_amount`, has not exceeded `max_uses`, and this customer hasn't exceeded `max_uses_per_customer`. Returns live discount amount preview and estimated total.
- **Permissions**: `IsAuthenticated` (Customer / Card Owner).
- **Request Body**:
```json
{
  "code": "SAVE20"
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Coupon 'SAVE20' applied successfully.",
  "data": {
    "coupon_code": "SAVE20",
    "discount_type": "percentage",
    "discount_value": "20.00",
    "discount_amount": "20.00",
    "subtotal": "100.00",
    "estimated_total": "80.00"
  }
}
```

### `POST /cards/{id}/remove-coupon/`
- **Description**: Customer removes the applied coupon from their draft memo card.
- **Permissions**: `IsAuthenticated` (Customer / Card Owner).
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Coupon removed from shopping memo.",
  "data": {
    "subtotal": "100.00",
    "discount_amount": "0.00",
    "estimated_total": "100.00"
  }
}
```

---

## 19. Store Customer Loyalty Points & Visit Stamp Cards APIs

### `GET /stores/{id}/loyalty-program/`
- **Description**: Retrieve public loyalty program rules and reward parameters for a store.
- **Permissions**: Public / `AllowAny`.
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Store loyalty program retrieved.",
  "data": {
    "id": 1,
    "store": 5,
    "store_name": "Daily Fresh Supermarket",
    "is_active": true,
    "program_type": "points",
    "points_per_currency_unit": "1.00",
    "currency_per_point_redemption": "0.0500",
    "min_points_to_redeem": 50,
    "stamps_for_reward": 10,
    "stamp_reward_discount_amount": "5.00",
    "min_order_for_stamp": "10.00"
  }
}
```

### `PATCH /stores/{id}/loyalty-program/`
- **Description**: Store vendor updates their store's loyalty program rules (switch between `points` and `stamps`, adjust redemption exchange rates, minimum points, reward amounts).
- **Permissions**: `IsAuthenticated` (Store Vendor or Staff).
- **Request Body**:
```json
{
  "is_active": true,
  "program_type": "stamps",
  "stamps_for_reward": 10,
  "stamp_reward_discount_amount": "5.00",
  "min_order_for_stamp": "10.00"
}
```

### `GET /stores/{id}/loyalty/`
- **Description**: Customer views their store-specific loyalty balance, visit stamps progress, reward eligibility, and recent ledger transactions for that store.
- **Permissions**: `IsAuthenticated` (Customer).
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Loyalty card summary for 'Daily Fresh Supermarket'.",
  "data": {
    "store_id": 5,
    "store_name": "Daily Fresh Supermarket",
    "is_program_active": true,
    "program_type": "stamps",
    "points_balance": 0,
    "stamps_balance": 8,
    "stamps_for_reward": 10,
    "stamps_needed": 2,
    "can_redeem": false,
    "potential_discount": "0.00",
    "recent_transactions": [...]
  }
}
```

### `GET /users/loyalty-cards/`
- **Description**: Customer views all their active store loyalty punch cards and point balances across all stores they shop at.
- **Permissions**: `IsAuthenticated` (Customer).

### `GET /stores/{id}/loyalty-customers/`
- **Description**: Vendor views top loyal customers, point balances, and visit counts for their store.
- **Permissions**: `IsAuthenticated` (Store Vendor or Staff).

### `POST /cards/{id}/redeem-loyalty/`
- **Description**: Applies store loyalty points or completed visit stamps reward directly to an active draft shopping memo, reducing the estimated total and budget consumption.
- **Permissions**: `IsAuthenticated` (Customer / Memo Owner).
- **Request Body (Points)**:
```json
{
  "points_to_redeem": 100
}
```
- **Request Body (Stamps)**:
```json
{
  "redeem_stamps": true
}
```
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Loyalty reward applied to shopping memo.",
  "data": {
    "points_redeemed": 100,
    "stamps_redeemed": 0,
    "loyalty_discount_amount": "5.00",
    "estimated_total": "45.00",
    "card": { ... }
  }
}
```

### `POST /cards/{id}/remove-loyalty/`
- **Description**: Removes applied loyalty discount from draft shopping memo.
- **Permissions**: `IsAuthenticated` (Customer / Memo Owner).

---

## 34. Customer Order Returns, Restocking & Thermal Credit Notes

### `POST /orders/returns/request/`
- **Description**: Customer initiates a return request for one or more items from a completed order.
- **Permissions**: `IsAuthenticated` (Customer / Order Owner).
- **Request Body**:
```json
{
  "order_id": 14,
  "reason": "damaged_defective",
  "reason_notes": "Carton leaked during delivery",
  "items": [
    {
      "order_item_id": 28,
      "quantity": "1.000"
    }
  ]
}
```
- **Response** (`201 Created`):
```json
{
  "success": true,
  "message": "Return request RET-A8F91B2C3D submitted successfully.",
  "data": {
    "id": 1,
    "return_number": "RET-A8F91B2C3D",
    "order": 14,
    "order_number": "ORD-5B7C2E1F0A",
    "store": 3,
    "store_name": "Green Valley Grocery",
    "status": "requested",
    "reason": "damaged_defective",
    "total_refund_amount": "45.00",
    "items": [
      {
        "id": 1,
        "product_name": "Organic Milk 1L",
        "quantity": "1.000",
        "unit_price": "45.00",
        "refund_subtotal": "45.00"
      }
    ]
  }
}
```

### `GET /orders/returns/`
- **Description**: List return requests. Customers view their own returns; vendors view returns for their store (`?as_vendor=true` or automatically scoped).
- **Permissions**: `IsAuthenticated`.
- **Query Parameters**:
  - `as_vendor`: `true` to list vendor store returns.
  - `store_id`: optional store filter.

### `POST /orders/returns/{id}/process/`
- **Description**: Store vendor approves or rejects a customer return request. If approved with `restock_inventory=true`, inventory is atomically restocked into `StockBalance.on_hand` with pessimistic row locking and logged to `StockLedgerEntry`. Reverses earned customer loyalty points/stamps proportionally.
- **Permissions**: `IsAuthenticated` (Store Vendor or Staff).
- **Request Body (Approval with Restock)**:
```json
{
  "decision": "approved",
  "restock_inventory": true
}
```
- **Request Body (Approval with Damage Write-Off)**:
```json
{
  "decision": "approved",
  "restock_inventory": false
}
```
- **Request Body (Rejection)**:
```json
{
  "decision": "rejected",
  "rejection_reason": "Seal was broken and item partially consumed."
}
```
- **Response** (`200 OK`): Returns updated `OrderReturn` with status `completed` or `rejected`.

### `GET /orders/returns/{id}/credit-note/?receipt_format=text`
- **Description**: Formatted 40-column monospace printable thermal credit note / return slip for POS thermal printers.
- **Permissions**: `IsAuthenticated` (Customer or Store Vendor).
- **Response** (`text/plain`):
```text
========================================
         GREEN VALLEY GROCERY
     CREDIT NOTE / RETURN RECEIPT
========================================
Date:                   2026-10-25 06:16 UTC
Return #:                     RET-A8F91B2C3D
Order #:                      ORD-5B7C2E1F0A
Customer:             customer@example.com
Status:                            Completed
Reason:                  Damaged / Defective
Restocked:                               Yes
----------------------------------------
ITEM                QTY x REFUND   TOTAL
----------------------------------------
Organic Milk 1L
  1.000 x 45.00                   -45.00
----------------------------------------
TOTAL REFUND:                     -45.00
Points Adjusted:                 -4 pts
----------------------------------------
     Refund processed successfully
 Keep this slip for your accounting records
========================================
```

---

## 20. Store Routine Basket Templates & One-Tap Memo Hydration

### `POST /cards/{id}/save-as-template/`
- **Description**: Save an existing draft shopping memo with all its line items into a named recurring routine template for that specific store (e.g. "Weekly Groceries", "Monthly Household Refill"). Automatically populates relational `user`, `store`, and `vendor` foreign keys.
- **Permissions**: `IsAuthenticated` (Customer owner only).
- **Request Body**:
```json
{
  "name": "Weekly Breakfast Routine",
  "description": "Organic whole milk and eggs for every Monday",
  "is_favorite": true
}
```
- **Response** (`201 Created`):
```json
{
  "success": true,
  "message": "Shopping memo saved as routine template 'Weekly Breakfast Routine'.",
  "data": {
    "id": 1,
    "name": "Weekly Breakfast Routine",
    "description": "Organic whole milk and eggs for every Monday",
    "user": 5,
    "store": 12,
    "store_name": "Fresh Fields Market",
    "vendor": 2,
    "vendor_email": "vendor@example.com",
    "shopping_mode": "remote",
    "is_favorite": true,
    "items": [
      {
        "id": 1,
        "product_id": 101,
        "product_name": "Organic Whole Milk 1L",
        "barcode": "8901234567890",
        "sku": "MILK-001",
        "aisle": "Dairy",
        "shelf_location": "D-02",
        "quantity": "2.000",
        "unit_price": "4.50",
        "subtotal": "9.00",
        "notes": "",
        "is_in_stock": true,
        "available_stock": "48.000",
        "created_at": "2026-10-25T08:18:05Z",
        "updated_at": "2026-10-25T08:18:05Z"
      }
    ],
    "total_items_count": 1,
    "estimated_total": "9.00",
    "created_at": "2026-10-25T08:18:05Z",
    "updated_at": "2026-10-25T08:18:05Z"
  },
  "errors": null
}
```

### `GET /cards/templates/`
- **Description**: List saved routine basket templates. Customers see their own templates; vendors can inspect customer routine lists created for their store using `?as_vendor=true`.
- **Permissions**: `IsAuthenticated`.
- **Query Parameters**:
  - `store_id`: optional integer filter for templates belonging to a specific store.
  - `is_favorite`: `true` or `false` to filter pinned/favorite routines.
  - `as_vendor`: `true` (Vendors only) to view customer templates scoped to their store(s).

### `POST /cards/templates/`
- **Description**: Create a routine basket template directly from scratch for a store.
- **Permissions**: `IsAuthenticated`.
- **Request Body**:
```json
{
  "store_id": 12,
  "name": "Monthly Pantry Essentials",
  "description": "Rice, oil, spices, and lentils",
  "shopping_mode": "walk_in",
  "is_favorite": true
}
```

### `GET /cards/templates/{id}/`
- **Description**: Retrieve a routine template with line items, dynamic catalog pricing recalculation, and stock availability check.
- **Permissions**: `IsAuthenticated` (Owner, Store Vendor, or Staff).

### `PATCH /cards/templates/{id}/`
- **Description**: Update template metadata (`name`, `description`, `shopping_mode`, `is_favorite`).
- **Permissions**: `IsAuthenticated` (Owner only).

### `DELETE /cards/templates/{id}/`
- **Description**: Soft delete routine template (`is_deleted=true`).
- **Permissions**: `IsAuthenticated` (Owner only).

### `POST /cards/templates/{id}/add-item/` (or `POST /cards/templates/{id}/items/`)
- **Description**: Add or update a product line item in the template. Rejects products from different stores.
- **Permissions**: `IsAuthenticated` (Owner only).
- **Request Body**:
```json
{
  "product_id": 105,
  "quantity": "3.000",
  "notes": "Prefer latest expiration batch"
}
```

### `DELETE /cards/templates/{id}/items/{item_id}/` (or `POST /cards/templates/{id}/remove-item/`)
- **Description**: Remove a line item from the routine template.
- **Permissions**: `IsAuthenticated` (Owner only).

### `POST /cards/templates/{id}/load-to-memo/`
- **Description**: **One-Tap Memo Hydration**. Loads the template's line items into the customer's active draft shopping memo for that store. Automatically evaluates real-time stock availability and live catalog prices. If any item is out of stock or inactive, it is gracefully omitted with descriptive feedback in `omitted_items` without aborting the hydration of available items.
- **Permissions**: `IsAuthenticated` (Owner only).
- **Request Body**:
```json
{
  "mode": "replace",
  "shopping_mode": "walk_in"
}
```
*`mode` options:*
- `"replace"` *(default)*: Replaces all line items in the active draft memo with items from this template.
- `"merge"`: Merges template items into the active memo, incrementing quantities for existing items up to available stock.
- **Response** (`200 OK`):
```json
{
  "success": true,
  "message": "Routine template loaded into active memo (2 loaded, 1 omitted).",
  "data": {
    "card": {
      "id": 15,
      "store": 12,
      "store_name": "Fresh Fields Market",
      "shopping_mode": "walk_in",
      "total_amount": "14.50",
      "items": [...]
    },
    "loaded_items_count": 2,
    "omitted_items_count": 1,
    "loaded_items": [
      {
        "item_id": 42,
        "product_id": 101,
        "product_name": "Organic Whole Milk 1L",
        "quantity": "2.000",
        "unit_price": "4.50",
        "subtotal": "9.00",
        "aisle": "Dairy",
        "shelf_location": "D-02"
      }
    ],
    "omitted_items": [
      {
        "product_id": 109,
        "product_name": "Sourdough Bread",
        "reason": "Product currently out of stock"
      }
    ]
  },
  "errors": null
}
```



