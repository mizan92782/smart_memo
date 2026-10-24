---
name: store-management
description: Vendor store profile, location, opening hours, delivery settings and store lifecycle.
---
# Store Management

## Rules
- Define store ownership and whether vendors may own multiple stores.
- Validate name, contact details, address, coordinates, opening hours and delivery configuration.
- Keep active/inactive state explicit; inactive stores should not appear as orderable unless policy allows it.
- Store location coordinates with validated latitude/longitude ranges.
- Keep customer-visible store profile fields separate from internal vendor metadata.
- Define safe archival/deactivation behavior for stores with historical orders.
- Every mutation must verify store ownership or delegated permission.

## Workflow
1. Define store model and ownership.
2. Add validation and migration.
3. Implement authorized CRUD and public detail/catalog views.
4. Add store status and opening-hours rules.
5. Test tenant access and customer discovery behavior.

## Acceptance checks
- Unauthorized vendors cannot modify a store.
- Historical orders remain readable after store deactivation.
- Invalid coordinates and malformed opening hours are rejected.
