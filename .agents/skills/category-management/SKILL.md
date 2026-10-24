---
name: category-management
description: Vendor-owned product category creation, updates, listing and archival.
---
# Category Management

## Rules
- Categories belong to a store or vendor according to the established tenant model.
- Enforce name uniqueness within the intended scope if required; normalize whitespace/case consistently.
- Validate category name, description, image and active status.
- Prevent cross-tenant product/category assignments.
- Prefer archival/deactivation over destructive deletion when products or historical order lines reference a category.
- Paginate category lists when they can grow; use stable ordering.
- Invalidate affected category/catalog caches after mutations.

## Acceptance checks
- A vendor cannot assign another tenant's category to a product.
- Deletion/archival does not corrupt historical order data.
- Duplicate and invalid category names are handled predictably.
