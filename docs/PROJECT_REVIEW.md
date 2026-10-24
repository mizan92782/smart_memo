# Smart Memo System — Comprehensive Project Review & Architectural Guide

## 1. Executive Summary

Smart Memo System is a multi-tenant SaaS application designed to connect local grocery and general stores with neighborhood customers. The platform facilitates store and catalog management, inventory ledger tracking, supplier purchasing, customer discovery, draft shopping memos, order fulfillment, and cash-on-delivery payments.

This document reviews the current codebase, evaluates architectural alignment with [AGENTS.md](file:///home/mizan/Desktop/smart_memo/AGENTS.md), details the project's layered architectural pattern, identifies technical debt, and provides an end-to-end development guide.

---

## 2. Architectural Pattern: Layered Clean Architecture

The codebase is migrating from traditional Django monolith structure to a **Layered Architecture (Repository-Service Pattern)**. Every domain app (`users`, `categories`, `products`, and future `stores`, `inventory`, `orders`) adheres to the following structural layers:

```
<app_name>/
├── models/             # Database entity schemas & Meta declarations
│   ├── __init__.py
│   └── <entity>_mod.py
├── repositories/       # Pure database query layer (static methods only, no business logic)
│   ├── __init__.py
│   └── <entity>_repository.py
├── services/           # Business logic, transaction boundaries, stock formulas
│   ├── __init__.py
│   └── <entity>_service.py
├── serializers/        # DRF input validation & response schemas
│   ├── __init__.py
│   └── <entity>_serializer.py
├── validators/         # Domain-specific validation rules
│   ├── __init__.py
│   └── <entity>_validator.py
├── views/              # API endpoints, request parsing, HTTP status dispatch
│   ├── __init__.py
│   └── <entity>_view.py
├── tests/              # Test suites (unit, integration, security)
│   ├── __init__.py
│   ├── test_<entity>.py
│   └── test_security.py
├── urls.py             # App route declarations
├── admin.py            # Django admin registration
└── apps.py             # AppConfig definition
```

### Layer Responsibilities & Rules
1. **Models (`models/`)**:
   - Must inherit from [`shared.base.base_model.BaseModel`](file:///home/mizan/Desktop/smart_memo/shared/base/base_model.py) (includes `created_at`, `updated_at`, `is_deleted`, `soft_delete()`, and `restore()`).
   - Store money as `DecimalField` (e.g. `max_digits=10, decimal_places=2`). Never use binary floating point.
   - Use `MeasurementUnit` and `CurrencyUnit` choices from `shared.enums`.
2. **Repositories (`repositories/`)**:
   - **Static methods only**. Never instantiate repository classes.
   - Single point of truth for ORM queries (`filter()`, `select_related()`, `prefetch_related()`, `aggregate()`).
   - Must enforce tenant scoping when querying store-scoped entities.
3. **Services (`services/`)**:
   - Encapsulates business logic, atomic transaction boundaries (`@transaction.atomic`), state machine transitions, and error raising.
   - Interacts with repositories; does not access raw HTTP request objects.
4. **Serializers (`serializers/`)**:
   - Extends [`BaseModelSerializer`](file:///home/mizan/Desktop/smart_memo/shared/base/base_serializer.py) or `DynamicFieldsModelSerializer`.
   - Never exposes internal tenant IDs or sensitive system fields.
5. **Views (`views/`)**:
   - Delegates business execution to services.
   - Dispatches standardized responses via [`custome_success_response`](file:///home/mizan/Desktop/smart_memo/shared/responses/responses.py) or [`custome_error_response`](file:///home/mizan/Desktop/smart_memo/shared/responses/responses.py).
   - Enforces DRF permission classes (`IsStoreOwner`, `IsCustomer`).

---

## 3. Evaluation Against Non-Negotiable Rules

| Non-Negotiable Rule | Current Codebase Status | Remediation Required |
|---|:---:|---|
| **Server-Side Tenant Isolation** | 🔴 Non-Compliant | Existing `Category` and `Product` models have no store/vendor FK; data is globally shared. |
| **Draft Memo vs. Order Separation** | ⚪ Not Started | Dedicated `memos` and `orders` apps must be implemented. |
| **State Machine Enforcement** | ⚪ Not Started | Orders state transitions must be guarded by valid transition tables. |
| **Database Transactions & Concurrency** | 🔴 Partial | No row-locking (`select_for_update()`) or inventory reservation mechanism exists yet. |
| **Decimal Precision for Money & Units** | 🟢 Compliant | `Product.price` and `stock` use `DecimalField`. |
| **Bounded Pagination** | 🟢 Scaffolding Ready | [`StandardResultsPagination`](file:///home/mizan/Desktop/smart_memo/shared/pagination/pagination.py) is implemented with `max_page_size=100`. |
| **Query Optimization & N+1 Prevention** | 🟡 Partial | Scaffolding in `scripts/test.py` tests `prefetch_related`, but tests are not integrated into CI. |
| **Object-Level Authorization** | 🟡 Scaffolding Ready | Custom permissions exist in `shared/permissions/`, but are not yet attached to active ViewSets. |

---

## 4. Current Blockers & Immediate Refactoring Steps

1. **Resolve Shared Utilities Export Collision**:
   - [`utilities/__init__.py`](file:///home/mizan/Desktop/smart_memo/utilities/__init__.py) imports `success_response` and `error_response`, but [`shared.utilities.custom_responser`](file:///home/mizan/Desktop/smart_memo/shared/utilities/custom_responser.py) defines `custome_success_response`.
   - Standardize alias exports in `shared/utilities/custom_responser.py` and `shared/responses/responses.py`.
2. **Activate Custom User Model**:
   - Add `users` and `shared` to `INSTALLED_APPS` in `smart_memo/settings.py`.
   - Configure `AUTH_USER_MODEL = 'users.User'`.
3. **Introduce Store Boundary**:
   - Create `Store` model in a dedicated `stores` app or under `users`.
   - Add `store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='categories')` to `Category`.
   - Add `store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='products')` to `Product`.
   - Remove invalid FK default `default="Others"` on `Product.category`.

---

## 5. Development Guide & Workflow

### 1. Creating a New Feature Layer
When adding a feature to an app:
1. Define the model in `<app>/models/<entity>_mod.py`, inheriting from `BaseModel`.
2. Expose the model in `<app>/models/__init__.py`.
3. Implement repository query methods in `<app>/repositories/<entity>_repository.py`.
4. Implement business logic and transaction boundaries in `<app>/services/<entity>_service.py`.
5. Implement DRF serializer in `<app>/serializers/<entity>_serializer.py`.
6. Implement API view in `<app>/views/<entity>_view.py` and register route in `<app>/urls.py`.
7. Write unit and security tests in `<app>/tests/`.

### 2. Running Migrations & System Checks
```bash
# Check Django configuration
python manage.py check

# Generate new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

### 3. Running Automated Tests
```bash
# Run all tests
python manage.py test

# Run tests for a specific app
python manage.py test categories
python manage.py test products
python manage.py test users

# Run tests with verbose output
python manage.py test --verbosity=2
```

### 4. Definition of Done
A feature is complete ONLY when:
- Repository, Service, Serializer, and View layers follow project conventions.
- Tenant isolation is strictly enforced server-side.
- All 6 dimensions of the API test matrix (Happy Path, Validation, Unauthenticated, Unauthorized, Cross-Tenant IDOR, Concurrency) are implemented.
- `python manage.py test` passes without errors.
- Documentation and `docs/FEATURE_TRACKER.md` are updated.
