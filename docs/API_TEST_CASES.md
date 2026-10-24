# Smart Memo System — Comprehensive API Test Case Catalog

This catalog outlines test cases for every API endpoint across the Smart Memo System SaaS. All test implementations must adhere to the standardized test matrix defined in [.agents/skills/testing/SKILL.md](file:///home/mizan/Desktop/smart_memo/.agents/skills/testing/SKILL.md) and [.agents/skills/security-testing/SKILL.md](file:///home/mizan/Desktop/smart_memo/.agents/skills/security-testing/SKILL.md).

---

## 1. Authentication & Identity Management

### Endpoint: `POST /api/v1/auth/register/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `AUTH-REG-01` | Successful customer registration | Happy Path | Valid unique email, strong password, full_name, role=`CUSTOMER` | `201 Created`, user and profile created, password hashed |
| `AUTH-REG-02` | Successful vendor registration | Happy Path | Valid unique email, strong password, role=`VENDOR` | `201 Created`, user with `VENDOR` role created |
| `AUTH-REG-03` | Duplicate email registration | Validation | Email that already exists (case-insensitive) | `400 Bad Request` or `409 Conflict`, clear error message |
| `AUTH-REG-04` | Weak password rejection | Validation | Password < 8 characters or all digits | `400 Bad Request` with password validation error |
| `AUTH-REG-05` | Invalid role injection | Security | Client sends role=`SUPERUSER` or `STAFF` | `400 Bad Request` or forced default to `CUSTOMER` |
| `AUTH-REG-06` | Rate limiting | Security | 6+ registration requests within 1 minute from same IP | `429 Too Many Requests` |

### Endpoint: `POST /api/v1/auth/login/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `AUTH-LOG-01` | Successful login | Happy Path | Correct email and password | `200 OK`, returns access token & refresh token |
| `AUTH-LOG-02` | Wrong password | Auth Failure | Valid email, incorrect password | `401 Unauthorized` |
| `AUTH-LOG-03` | Nonexistent email | Auth Failure | Email not in database | `401 Unauthorized` (does not leak email existence) |
| `AUTH-LOG-04` | Inactive user login | Security | User with `is_active=False` | `403 Forbidden` / `401 Unauthorized` |
| `AUTH-LOG-05` | Brute-force rate limiting | Security | 6+ consecutive failed logins in 1 minute | `429 Too Many Requests` |

### Endpoint: `GET /api/v1/users/profile/` & `PUT /api/v1/users/profile/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `AUTH-PRF-01` | Read own profile | Happy Path | Authenticated User token | `200 OK`, returns user's profile details |
| `AUTH-PRF-02` | Unauthenticated read | Security | No auth header | `401 Unauthorized` |
| `AUTH-PRF-03` | Update profile fields | Happy Path | `phone_number`, `full_name`, `address` | `200 OK`, profile updated |
| `AUTH-PRF-04` | Mass assignment attempt | Security | Request contains `is_superuser=True`, `is_staff=True` | `is_superuser` is ignored/rejected; user remains unprivileged |

---

## 2. Store Management

### Endpoint: `POST /api/v1/stores/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `STORE-CRT-01` | Vendor creates store | Happy Path | Authenticated Vendor, valid store name, address, coordinates | `201 Created`, store linked to `vendor=request.user` |
| `STORE-CRT-02` | Customer attempts to create store | Security | Authenticated Customer token | `403 Forbidden` (only Vendors can manage stores) |
| `STORE-CRT-03` | Invalid coordinates | Validation | `latitude=120.0` (out of bounds) | `400 Bad Request` |
| `STORE-CRT-04` | Duplicate store slug | Validation | Store name generating an existing slug | Auto-suffixed or `400 Bad Request` |

### Endpoint: `GET /api/v1/stores/mine/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `STORE-LST-01` | Vendor lists their stores | Happy Path | Vendor A with 2 stores | `200 OK`, returns exactly Vendor A's 2 stores |
| `STORE-LST-02` | Tenant isolation check | Security | Vendor A requests list | Stores owned by Vendor B are completely excluded |

### Endpoint: `PUT /api/v1/stores/{id}/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `STORE-UPD-01` | Vendor updates own store | Happy Path | Vendor A updates Store A name, opening hours | `200 OK`, store updated |
| `STORE-UPD-02` | Cross-tenant IDOR update | Security | Vendor A attempts to update Store B owned by Vendor B | `404 Not Found` or `403 Forbidden` |
| `STORE-UPD-03` | Vendor reassignment tamper | Security | Vendor A sends `vendor_id=VendorB.id` in payload | Ignored; vendor ownership remains immutable |

### Endpoint: `GET /api/v1/stores/public/` & `GET /api/v1/stores/public/{id}/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `STORE-PUB-01` | Public discovery of active stores | Happy Path | Any user (anonymous or customer) | `200 OK`, lists active stores with public fields |
| `STORE-PUB-02` | Inactive store hidden from public | Business Rule | Store has `is_active=False` | Excluded from public list; detail view returns `404` |
| `STORE-PUB-03` | Private metadata hidden | Security | Public store detail response inspected | Internal supplier data, financial margins not included |

---

## 3. Category Management

### Endpoint: `POST /api/v1/categories/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `CAT-CRT-01` | Create store-scoped category | Happy Path | Vendor A, `name="Beverages"` | `201 Created`, category created for Vendor A's store |
| `CAT-CRT-02` | Duplicate category in same store | Validation | Vendor A creates "Beverages" again in same store | `400 Bad Request` (unique constraint on store+name) |
| `CAT-CRT-03` | Same category name in different store | Tenancy | Vendor B creates "Beverages" in Store B | `201 Created` (names are independent across stores) |
| `CAT-CRT-04` | Customer attempts category creation | Security | Customer token | `403 Forbidden` |

### Endpoint: `PUT/PATCH /api/v1/categories/{id}/` & `DELETE /api/v1/categories/{id}/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `CAT-UPD-01` | Update own category | Happy Path | Vendor A updates Category A name | `200 OK`, category name capitalized |
| `CAT-UPD-02` | Cross-tenant IDOR update | Security | Vendor A targets Category B (Store B) | `404 Not Found` |
| `CAT-DEL-01` | Delete empty category | Happy Path | Vendor A deletes category with 0 products | `204 No Content` |
| `CAT-DEL-02` | Delete category with active products | Business Rule | Category has 5 active products | `400 Bad Request` (must reassign or soft delete) |
| `CAT-DEL-03` | Cross-tenant IDOR delete | Security | Vendor A targets Category B (Store B) | `404 Not Found` |

---

## 4. Product & Pricing Management

### Endpoint: `POST /api/v1/products/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `PROD-CRT-01` | Create valid product | Happy Path | Vendor A, valid name, price=150.00, unit="kg", measure=1 | `201 Created`, linked to Store A, tags generated |
| `PROD-CRT-02` | Cross-store category assignment | Security | Vendor A assigns Category B (belonging to Store B) | `400 Bad Request` (category must belong to same store) |
| `PROD-CRT-03` | Negative price rejection | Validation | `price=-20.00` | `400 Bad Request` |
| `PROD-CRT-04` | Invalid measurement unit | Validation | `unit="lightyears"` | `400 Bad Request` |
| `PROD-CRT-05` | Offer calculation | Business Rule | `price=100.00`, `offered_discount=20.00` | `201 Created`, `offered_price` automatically calculated as `80.00` |

### Endpoint: `PUT/PATCH /api/v1/products/{id}/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `PROD-UPD-01` | Update own product | Happy Path | Vendor A updates price and description | `200 OK`, product updated |
| `PROD-UPD-02` | Cross-tenant IDOR update | Security | Vendor A updates Product B (Store B) | `404 Not Found` |
| `PROD-UPD-03` | Direct stock override rejection | Security | Vendor attempts `{"stock": 1000}` in product update | Ignored/Rejected; stock changes require inventory ledger |

### Endpoint: `GET /api/v1/catalog/products/` (Public Discovery)
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `PROD-PUB-01` | Search products by name/SKU | Happy Path | `?search=apple` | `200 OK`, returns paginated matching active products |
| `PROD-PUB-02` | Inactive product hidden | Business Rule | Product has `is_active=False` | Excluded from public search |
| `PROD-PUB-03` | Query count assertion | Performance | List 20 products | Verified $\le 4$ SQL queries (no N+1 on category/store) |

---

## 5. Inventory Ledger & Supplier Purchases

### Endpoint: `POST /api/v1/purchases/receive/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `INV-REC-01` | Receive purchase from supplier | Happy Path | Vendor A receives 50 kg of Product A at 80.00/kg | `201 Created`, `StockBalance.on_hand` increases by 50, `StockLedgerEntry(PURCHASE_RECEIVE)` logged |
| `INV-REC-02` | Receive purchase for foreign product | Security | Vendor A receives stock for Product B (Store B) | `404 Not Found` |
| `INV-REC-03` | Negative receive quantity | Validation | `quantity=-10` | `400 Bad Request` |
| `INV-REC-04` | Idempotent purchase receipt | Concurrency | Same purchase receipt submitted twice | Second request recognized as duplicate, no double stock |

### Endpoint: `POST /api/v1/inventory/adjust/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `INV-ADJ-01` | Log damaged stock | Happy Path | Vendor logs -2 kg damage with reason "spoilage" | `201 Created`, `on_hand` decreased by 2, audit entry created |
| `INV-ADJ-02` | Adjustment driving stock below zero | Invariant | Adjusting -100 kg when on_hand = 10 kg | `400 Bad Request` (database check constraint prevents negative stock) |
| `INV-ADJ-03` | Cross-tenant IDOR adjustment | Security | Vendor A targets Product B (Store B) | `404 Not Found` |

---

## 6. Draft Shopping Memos

### Endpoint: `GET/POST /api/v1/memos/current/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `MEMO-CUR-01` | Customer gets or creates draft memo | Happy Path | Authenticated Customer A for Store A | `200 OK`, returns active draft memo |
| `MEMO-CUR-02` | Cross-customer memo isolation | Security | Customer A requests current memo | Never sees Customer B's draft memo |
| `MEMO-CUR-03` | Draft memo does not alter stock | Invariant | Customer adds 10 items to draft memo | `StockBalance.on_hand` and `StockBalance.reserved` remain unchanged |

### Endpoint: `POST /api/v1/memos/current/items/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `MEMO-ITM-01` | Add item to draft memo | Happy Path | Customer A adds Product A (Store A), quantity=2 | `200 OK`, memo subtotal calculated |
| `MEMO-ITM-02` | Cross-store product addition | Multi-Tenant | Customer attempts adding Product B (Store B) to Store A memo | `400 Bad Request` (memos cannot mix stores) |
| `MEMO-ITM-03` | Inactive product addition | Validation | Adding product with `is_active=False` | `400 Bad Request` |
| `MEMO-ITM-04` | Quantity $\le 0$ rejection | Validation | `quantity=0` or `quantity=-1` | `400 Bad Request` |

---

## 7. Order Lifecycle & Reservations

### Endpoint: `POST /api/v1/orders/submit/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `ORD-SUB-01` | Submit order with available stock | Happy Path | Customer submits draft memo with idempotency key | `201 Created`, Order created in `SUBMITTED` state, stock reserved |
| `ORD-SUB-02` | Insufficient stock submission | Invariant | Item quantity=10, but `available` stock=5 | `400 Bad Request`, order rejected, transaction rolled back |
| `ORD-SUB-03` | Duplicate submission retry | Concurrency | Client sends identical idempotency key twice | Returns existing order without double reservation |
| `ORD-SUB-04` | Concurrent oversell attempt | Concurrency | 2 users submit order for last remaining 1 unit simultaneously | Exactly 1 order succeeds (201); 2nd fails (400) |

### Endpoint: `POST /api/v1/orders/{id}/accept/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `ORD-ACC-01` | Vendor accepts submitted order | Happy Path | Vendor A accepts Order A | `200 OK`, order transitions to `ACCEPTED` |
| `ORD-ACC-02` | Cross-tenant IDOR acceptance | Security | Vendor A attempts to accept Order B (Store B) | `404 Not Found` |
| `ORD-ACC-03` | Invalid state transition | State Machine | Vendor attempts accepting already `COMPLETED` order | `400 Bad Request` |

### Endpoint: `POST /api/v1/orders/{id}/cancel/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `ORD-CAN-01` | Customer cancels submitted order | Happy Path | Customer cancels pending order | `200 OK`, order status=`CANCELLED`, reserved stock released |
| `ORD-CAN-02` | Vendor rejects order | Happy Path | Vendor rejects submitted order | `200 OK`, order status=`REJECTED`, reserved stock released |
| `ORD-CAN-03` | Cancel already fulfilled order | State Machine | Cancelling order with status=`COMPLETED` | `400 Bad Request` (cannot cancel fulfilled orders) |

### Endpoint: `POST /api/v1/orders/{id}/fulfill/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `ORD-FUL-01` | Complete fulfillment & cash collection | Happy Path | Vendor fulfills order, marks COD collected | `200 OK`, order=`COMPLETED`, payment=`COLLECTED`, stock deducted from on_hand & reserved, Sales Memo generated |
| `ORD-FUL-02` | Cross-tenant IDOR fulfillment | Security | Vendor A fulfills Order B | `404 Not Found` |

---

## 8. Reporting & Analytics

### Endpoint: `GET /reports/sales/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `REP-SLS-01` | Vendor sales report | Happy Path | Vendor A requests sales report for date range | `200 OK`, aggregates revenue from Store A only |
| `REP-SLS-02` | Tenant isolation in analytics | Security | Vendor A requests report | Zero data from Vendor B is included in totals |
| `REP-SLS-03` | Customer access blocked | Security | Customer token calls sales report endpoint | `403 Forbidden` |
| `REP-INV-01` | Low stock threshold alert | Happy Path | Available stock <= low_stock_threshold | Included in `low_stock_items` array |
| `REP-PUR-01` | Purchases procurement summary | Happy Path | Received purchase orders total aggregated | Accurate sum of total_cost for received POs |

---

## 9. Purchases & Supplier Directory

### Endpoint: `POST /purchases/suppliers/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `PUR-SUP-01` | Vendor creates supplier | Happy Path | Valid store, supplier name, contact | `201 Created`, supplier saved to database |
| `PUR-SUP-02` | Cross-tenant supplier creation | Security | Vendor B attempts creating supplier for Store A | `403 Forbidden` |
| `PUR-SUP-03` | Customer supplier creation block | Security | Customer token attempts creating supplier | `403 Forbidden` |

### Endpoint: `POST /purchases/orders/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `PUR-ORD-01` | Create purchase order draft | Happy Path | Store ID, Supplier ID, item quantities & costs | `201 Created`, status=`draft`, inventory untouched |
| `PUR-ORD-02` | Submit purchase order | State Machine | Status transitions `draft` -> `submitted` | `200 OK`, inventory untouched |
| `PUR-ORD-03` | Cross-tenant PO creation | Security | Vendor B specifies Store A or Supplier A | `403 Forbidden` |

### Endpoint: `POST /purchases/orders/{id}/receive/`
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `PUR-REC-01` | Confirm goods receipt | Happy Path | Status transitions to `received` | `200 OK`, `StockBalance.on_hand` increased, `StockLedgerEntry` logged |
| `PUR-REC-02` | Duplicate receive rejected | Idempotency | Calling receive on already received PO | `400 Bad Request`, stock cannot be double-counted |
| `PUR-REC-03` | Cross-tenant PO receive | Security | Vendor B calls receive on Vendor A's PO | `404 Not Found` (IDOR block) |

---

## 10. Performance & N+1 Query Optimization

### Query Counting Tests
| Test ID | Test Scenario | Type | Request Payload / State | Expected Result |
|---|---|---|---|---|
| `PERF-CAT-01` | Catalog product search | Performance | Search query returning multiple products | `assertNumQueries(2)`: 1 COUNT query, 1 SELECT query with category & store JOINs |
| `PERF-ORD-01` | Order collection listing | Performance | Vendor listing multiple orders with line items & memos | `assertNumQueries(4)`: 1 COUNT, 1 Orders SELECT with customer & store JOINs, 1 items prefetch, 1 memo prefetch |

