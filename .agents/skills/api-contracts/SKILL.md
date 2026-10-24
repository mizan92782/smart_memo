---
name: api-contracts
description: Consistent API schemas, validation, errors, versioning and documentation.
---
# API Contracts

## Rules
- Follow the project's established API style and naming conventions.
- Define request/response schemas explicitly and validate at the boundary.
- Return consistent error shapes and appropriate status codes.
- Never expose internal model fields by default; use response schemas/serializers.
- Document pagination, filters, sorting, permissions, side effects and state transitions.
- Make API changes backwards-compatible where practical; version breaking changes deliberately.
- Avoid returning inconsistent numeric types for money and measurement quantities.
- Do not leak cross-tenant existence through overly specific errors.

## Acceptance checks
- OpenAPI or equivalent documentation matches implementation.
- Invalid inputs and unauthorized access produce consistent errors.
- Response schemas do not expose private fields.
