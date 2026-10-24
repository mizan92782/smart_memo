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
  - `search` (string, optional): Searches name, second_name, tags
  - `page`, `page_size`

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

### `GET /orders/{id}/sales_memo/`
- **Description**: Download or view finalized immutable sales memo receipt.
- **Permissions**: `IsAuthenticated` (Order Customer or Store Vendor).

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
- **Description**: Returns or auto-initializes the authenticated customer's current active draft shopping memo.
- **Permissions**: `IsAuthenticated`.
- **Response**: `200 OK` with `Card` object containing `items`, `store`, `store_name`, and `total_price`.

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
- **Description**: Converts customer's draft shopping memo card into a submitted order with atomic inventory reservation and catalog price/offer revalidation.
- **Permissions**: `IsAuthenticated` (Card owner only).
- **Request Body**:
```json
{
  "fulfillment_type": "delivery",
  "delivery_address": "Flat 4B, Green Road, Dhaka",
  "notes": "Ring bell on arrival",
  "idempotency_key": "chk-98a0f2b3"
}
```
- **Response**: `201 Created` with snapshot `Order` object.

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




