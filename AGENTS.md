# Smart Memo System — Agent Instructions

## Mission
Build and maintain Smart Memo System, a multi-tenant SaaS connecting local stores/vendors and customers. Vendors manage stores, categories, products, pricing, inventory, suppliers, purchases, offers, sales and orders. Customers discover nearby stores, search products, create memos, favorite stores, order pickup/home delivery, and pay cash on delivery where supported.

## Before every task
1. Inspect the repository, current conventions, dependencies, tests, and existing implementation.
2. Read `.agents/skills/saas-architecture/SKILL.md` and `.agents/skills/security-tenant-isolation/SKILL.md`; then read skills relevant to the task.
3. Write a concise plan for non-trivial changes: business behavior, data changes, permissions, transactions, queries/cache, tests, docs.
4. Implement one bounded feature at a time.
5. Run relevant tests and checks. Never claim a command passed unless it ran successfully.
6. Update the relevant skill with reusable decisions or patterns discovered.
7. Whenever backend APIs, models, or business workflows change, update `docs/FRONTEND_BACKEND_SYNC_TRACKER.md` and correspondingly update the frontend in `/home/mizan/Desktop/Smart_Memo_Frontend` to maintain full-stack parity.

## Non-negotiable engineering rules
- Enforce tenant isolation server-side. Never trust a client-provided tenant/store ID without authorization checks.
- Treat draft memos differently from submitted orders and completed sales.
- Define and validate state transitions. Do not permit arbitrary status changes.
- Use database transactions for multi-record business operations.
- Protect inventory from concurrent overselling using database constraints, row locks, or conditional updates appropriate to the chosen database.
- Store money as decimal or integer minor units; do not use binary floating point for financial calculations.
- Use suitable decimal precision for weight/volume inventory.
- Use pagination for potentially large collections, stable ordering, and a maximum page size.
- Prevent N+1 queries with the ORM's eager-loading/prefetching or equivalent; test query counts for important endpoints.
- Cache only where appropriate; include tenant/context in keys and invalidate on writes. Never treat cached stock or price as authoritative at checkout.
- Validate input and enforce object-level permissions in the backend.
- Add automated tests for business rules, authorization, failures, and relevant concurrency/data integrity cases.
- Avoid unnecessary dependencies, premature microservices, and unrelated refactoring.
- Do not perform destructive migrations or data changes without a safe migration plan.

## Suggested implementation sequence
1. Architecture, authentication, roles, tenant isolation.
2. Store, category, product, unit, pricing and offers.
3. Inventory ledger, suppliers, purchase receiving.
4. Catalog search, draft memos, favorites.
5. Orders, reservation policy, fulfillment and cancellation.
6. Delivery/pickup, payment/COD, finalized sales memos.
7. Reports, notifications, low-stock alerts.
8. Production hardening, deployment, monitoring, performance.

## Definition of done
A feature is done when business behavior, validation, authorization, tenant isolation, data integrity, relevant caching/pagination/query optimization, automated tests, documentation, frontend UI alignment and sync tracking (`docs/FRONTEND_BACKEND_SYNC_TRACKER.md`), and a concise implementation report are complete.
