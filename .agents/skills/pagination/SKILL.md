---
name: pagination
description: Consistent, bounded, stable pagination for API collection endpoints.
---
# Pagination

## Rules
- Paginate every potentially unbounded collection.
- Validate page, limit, cursor and sort parameters; set a reasonable maximum page size.
- Use stable ordering with a unique tie-breaker.
- Return a consistent response shape and metadata across the API.
- Prefer cursor/keyset pagination for very large or frequently changing collections where justified.
- Avoid loading the entire result set to compute totals unless required and affordable.
- Apply tenant/authorization filters before pagination.
- Ensure filters and ordering are indexed where query volume warrants it.
- Test empty pages, invalid parameters, maximum limits, duplicate sort values and changing data.

## Acceptance checks
- No endpoint accidentally returns an unbounded collection.
- Pagination has deterministic ordering.
- Authorization filtering cannot be bypassed by page/cursor manipulation.
