---
name: testing
description: Test strategy for business logic, API behavior, tenancy, transactions, concurrency and performance.
---
# Testing Strategy

## Core Principles
1. **Behavior Over Implementation**: Test contracts, invariants, and business outcomes rather than private method calls.
2. **Layered Test Architecture**:
   - **Repository Tests**: Verify raw query filtering, database constraints, soft deletes, and custom model managers.
   - **Service Tests**: Verify business rules, transaction boundaries, stock calculations, state machine transitions, and error raising.
   - **API / ViewSet Tests**: Verify HTTP status codes, payload structures, pagination, validation errors, and response formatting.
   - **Security Tests**: Verify tenant isolation, RBAC role boundaries, IDOR prevention, and authentication.
3. **Deterministic & Isolated Data**:
   - Each test method creates its own test fixtures (Vendors, Stores, Customers, Products).
   - Never rely on database state from a previous test.
4. **Integration with Real Database Capabilities**:
   - For transactional row locking (`select_for_update()`) and database constraints, verify tests execute against PostgreSQL or compliant engine.
5. **No Silent Passing**:
   - Never mock away business critical invariants (e.g. stock reservation logic or permission checks).
   - Never claim a test passed unless verified by actual execution output.

## Required Test Matrix for Every API Endpoint
Every API endpoint must provide test cases across 6 standardized dimensions:

| Dimension | Description | Expected Status |
|---|---|---|
| **1. Happy Path** | Valid request payload and authorized actor | `200 OK` / `201 Created` / `204 No Content` |
| **2. Validation Failure** | Missing required fields, malformed types, negative numbers | `400 Bad Request` with structured error details |
| **3. Unauthenticated** | Request without Bearer token or session | `401 Unauthorized` |
| **4. Permission Denied** | Authenticated actor lacks required role (e.g. Customer calling Vendor API) | `403 Forbidden` |
| **5. Cross-Tenant IDOR** | Vendor A attempts to read/mutate Vendor B's resources | `404 Not Found` or `403 Forbidden` |
| **6. Concurrency / Invariant** | Simultaneous operations violating invariant (e.g. overselling last item) | Atomic rollback + `400 Bad Request` |

## Query Count & N+1 Prevention
- Use `assertNumQueries` on high-traffic list and detail endpoints:
  - List endpoints must maintain flat query counts (e.g. $\le 4$ queries regardless of page size) using `select_related` and `prefetch_related`.
  - Regression tests must catch any newly introduced N+1 loops.

## Concurrency Testing Pattern
To test inventory concurrency:
```python
from django.db import transaction
from django.test import TransactionTestCase

class ConcurrentOrderTests(TransactionTestCase):
    def test_concurrent_reservations_cannot_oversell(self):
        # Set up store, product with stock = 1
        # Attempt two concurrent reservations via threads or sequential transactions
        # Verify exactly one succeeds and second raises InsufficientStockException
```

## Acceptance Checks
- 100% of API endpoints have corresponding test suites covering all 6 dimensions.
- All tests pass via `python manage.py test`.
- Tenant isolation tests pass with multiple stores.
- Failed tests are diagnosed and fixed before completing a feature.
