---
name: security-testing
description: Security test suites, tenant isolation verification, IDOR prevention, permission checks, and abuse controls.
---
# Security Testing

## Use when
Writing automated security tests, conducting code reviews for data leaks, validating tenant isolation, testing authentication/authorization barriers, and preventing abuse (rate-limiting, mass assignment, IDOR).

## Core Rules
1. **Multi-Tenant Isolation Verification**:
   - Every multi-tenant endpoint MUST be tested with at least two isolated tenants: `Tenant A` (Store A / Vendor A) and `Tenant B` (Store B / Vendor B).
   - Test that Tenant A cannot access, update, delete, or list any entity owned by Tenant B (`404 Not Found` or `403 Forbidden`).
   - Test that passing `store_id` or `vendor_id` of Tenant B in request body or URL path fails safely and cannot bypass server-side context resolution.
2. **Customer Privacy Verification**:
   - Customer A must NEVER be able to read or modify Customer B's draft memo, order history, phone number, or delivery address.
   - Customers must NEVER see vendor-private data (e.g., supplier names, wholesale purchase costs, raw inventory ledger entries, or store financial metrics).
3. **Insecure Direct Object Reference (IDOR) Checks**:
   - For every endpoint taking an ID (e.g. `/api/v1/orders/{id}/`, `/api/v1/categories/{id}/`, `/api/v1/products/{id}/`):
     - Test with valid ID owned by the user -> Success (200/204).
     - Test with valid ID owned by *another* user/store -> 404/403.
     - Test with nonexistent ID -> 404.
4. **Authentication & Token Lifecycle**:
   - Unauthenticated requests to protected endpoints must return `401 Unauthorized`.
   - Expired, tampered, or blacklisted tokens must be rejected with `401 Unauthorized`.
   - Password reset tokens must be single-use and invalidated immediately upon use or expiry.
5. **Role Escalation & RBAC Boundaries**:
   - A `CUSTOMER` account must never be able to access `VENDOR`, `STAFF`, or `SUPERUSER` actions.
   - A `VENDOR` account cannot access platform-wide administrative endpoints.
6. **Mass Assignment & Field Tampering**:
   - Read-only and sensitive fields (e.g. `role`, `is_superuser`, `is_staff`, `store_id`, `offered_price`, `balance_after`) must be ignored or rejected if passed in request payloads.
7. **Rate Limiting & Abuse Prevention**:
   - Sensitive endpoints (Login, Signup, OTP generation, Password Reset, Checkout) must have throttling tests verifying `429 Too Many Requests` after quota exhaustion.
8. **Data Leakage & Safe Errors**:
   - Responses must never leak stack traces, database schema names, internal IP addresses, SQL queries, or plain-text credentials.

## Standard Security Test Suite Structure
For every API module, implement a dedicated `test_security.py`:
- `test_unauthenticated_access_rejected()`
- `test_cross_tenant_read_rejected()`
- `test_cross_tenant_update_rejected()`
- `test_cross_tenant_delete_rejected()`
- `test_customer_cannot_access_vendor_endpoints()`
- `test_vendor_cannot_escalate_to_superuser()`
- `test_mass_assignment_protection()`
- `test_rate_limiting()`

## Acceptance Checks
- All security test cases run and pass under automated CI (`python manage.py test`).
- No endpoint relies on client-side trust for authorization.
- Zero IDOR vulnerabilities detected across all CRUD operations.
