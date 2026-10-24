---
name: nearby-store-discovery
description: Location-based store discovery, distance ranking, radius and location fallback.
---
# Nearby Store Discovery

## Rules
- Request and use customer location only with appropriate permission and product policy.
- Validate coordinates and search radius.
- Use indexed geospatial queries when supported; otherwise use a measured, indexed coordinate strategy.
- Filter inactive/unavailable stores according to documented discovery rules.
- Apply stable sorting, pagination, and a maximum radius/result limit.
- Do not expose exact private addresses or sensitive vendor data beyond the intended public store profile.
- Provide manual location, address/area search, or non-location store browsing when permission is denied.
- Calculate distance consistently and test boundary conditions.

## Acceptance checks
- Nearby results are ordered according to the documented distance/ranking policy.
- Invalid coordinates and extreme radius values are rejected.
- Location denial does not make the app unusable.
- Large result sets are paginated efficiently.

## Verified Implementation Pattern
- **Haversine Distance**: Computed with Earth's radius $R = 6371.0\text{ km}$ after database-level bounding box pre-filtering (`latitude__gte`, `latitude__lte`, `longitude__gte`, `longitude__lte`), ensuring zero proprietary database dependency and identical execution across SQLite testing and PostgreSQL production.
- **Coordinate Validation**: Validates `lat` between -90.0 and 90.0, `lng` between -180.0 and 180.0, and `radius_km` between 0.1 and 100.0 (default 10.0km).
- **Graceful Fallback**: Missing coordinates trigger non-location store browsing without crashing, returning active stores sorted stably.
- **Output Schema**: `PublicStoreSerializer` exposes read-only `distance_km` (rounded to 2 decimal places) and tenant-safe public attributes.

