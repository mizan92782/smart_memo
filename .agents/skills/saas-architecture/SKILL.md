---
name: saas-architecture
description: Shared architecture and domain boundaries for the multi-vendor Smart Memo System SaaS.
---
# SaaS Architecture

## Use when
Starting the project, changing module boundaries, introducing shared services, or making a cross-cutting design decision.

## Domain modules
- Identity and access
- Vendor/store management
- Catalog: categories, products, units, prices, offers
- Inventory ledger
- Suppliers and purchase receiving
- Customer memos and orders
- Fulfillment: pickup, delivery, status tracking
- Payments and cash-on-delivery collection
- Sales documents/receipts
- Favorites and store discovery
- Reporting, notifications, audit and platform administration

## Rules
- Inspect the existing stack before proposing replacements.
- Prefer a modular monolith initially unless measured scale or team boundaries justify services.
- Keep business rules in domain/service layers rather than route/controller handlers.
- Keep inventory, purchasing, orders, payments and sales as separate concepts with explicit transactional boundaries.
- Use stable IDs and explicit foreign keys. Add indexes based on access patterns.
- Use UTC for persisted timestamps unless the existing system has a documented alternative; display in the relevant timezone.
- Keep API contracts documented and version changes deliberately.
- Separate public catalog fields from vendor-private costs, supplier data and internal reports.
- Record architectural decisions in an ADR or architecture document.

## Workflow
1. Map current modules and dependencies.
2. Identify the domain owner for each new behavior.
3. Define contracts and transaction boundaries.
4. Check authorization, concurrency, cache, pagination and test implications.
5. Implement the smallest coherent change.

## Acceptance checks
- Module responsibilities are clear.
- Cross-module workflows have explicit consistency rules.
- No needless microservices or duplicated business logic.
- Architecture decisions and trade-offs are documented.
