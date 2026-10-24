---
name: query-optimization
description: ORM loading strategies, N+1 prevention, indexes and query measurement.
---
# Query Optimization and N+1 Prevention

## Rules
- Inspect query counts and query plans for important endpoints.
- Use ORM eager loading, prefetching, joins, projections or aggregation as appropriate.
- Avoid database queries inside loops over result records.
- Do not over-fetch large blobs or private fields.
- Add indexes based on real filters, joins, uniqueness and ordering patterns.
- Watch for join fan-out and duplicated rows when loading multiple collections.
- Use bulk operations where they preserve business rules and signals/hooks.
- Paginate before serializing large collections.
- Cache only after query shape and invalidation behavior are understood.

## Acceptance checks
- Tests or instrumentation detect regressions in key endpoint query counts.
- List endpoints do not execute one related-object query per row.
- Index migrations and query plans are reviewed for high-volume access paths.
