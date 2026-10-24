---
name: security-tenant-isolation
description: Authentication, authorization, ownership checks, and tenant data separation.
---
# Security and Tenant Isolation

## Use when
Implementing any authenticated endpoint, store-scoped data, vendor/customer access, staff roles, or platform administration.

## Rules
- Resolve identity from the trusted authentication mechanism.
- Resolve tenant/store membership server-side and verify the actor's permission for every object.
- Never rely on hidden UI controls or a client-supplied `vendor_id`, `store_id`, or role.
- Apply tenant filters to reads, updates, deletes, exports, background jobs, and nested resources.
- Avoid insecure direct object references: test access using IDs belonging to another tenant.
- Customers may see only public catalog data and their own permitted orders/memos; vendor-private supplier, cost, stock ledger, and reporting data remain private.
- Use least privilege and explicit role/permission checks.
- Validate uploads, rate-limit sensitive endpoints, protect secrets, and avoid logging tokens or sensitive personal data.
- Use safe errors that do not disclose another tenant's records.

## Tests
- Vendor A cannot read or mutate Vendor B's store, product, purchase, inventory or order-management data.
- Customer A cannot read Customer B's private order or address.
- Changing an object ID in a request does not bypass authorization.
- Background tasks and exports enforce the same tenant boundaries.
- Unauthenticated and insufficiently authorized requests fail safely.
