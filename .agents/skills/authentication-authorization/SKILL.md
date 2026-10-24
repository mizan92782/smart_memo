---
name: authentication-authorization
description: Secure identity lifecycle, login, sessions/tokens, and role-based authorization.
---
# Authentication and Authorization

## Use when
Building registration, login, logout, verification, password recovery, token/session handling, or role permissions.

## Rules
- Reuse the project's established identity framework where possible.
- Store passwords only using a proven password-hashing implementation.
- Never log credentials, tokens, reset links, or verification secrets.
- Keep authentication separate from authorization: a logged-in actor is not automatically permitted to access every resource.
- Define allowed roles and actions explicitly; check permissions on the server.
- Use secure, expiring, single-use password reset and verification flows.
- Rate-limit login, registration, recovery and verification endpoints.
- Revoke/expire sessions or refresh tokens appropriately on logout, password reset, or account disablement.
- Avoid leaking whether an email account exists in recovery responses where that creates risk.

## Acceptance checks
- Valid and invalid login paths are tested.
- Expired, revoked, malformed and wrong-role credentials are rejected.
- Passwords and tokens are not returned in API responses or logs.
- Authorization is tested at object level, not just by role.
