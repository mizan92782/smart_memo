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

## Verified Architecture Patterns
- **Token Invalidation on Password Change**: When a user changes their password (`POST /users/change-password/`), always rotate the auth token (`UserRepository.rotate_token`) immediately to invalidate any compromised tokens or stale sessions.
- **Disabled Account Handling**: Django's default `authenticate()` returns `None` for inactive users. Check user existence and password validity explicitly to return `PermissionDenied` (`403 Forbidden`) when an inactive account attempts login, rather than a generic `400/401`.
- **Profile Signal Connections**: Ensure `ready()` in `apps.py` registers `users.signals` so that newly created users automatically have an associated `Profile` record. In `register_user`, update the profile's `full_name` directly if provided during registration.
- **Strict Profile Isolation**: Never accept a client-supplied user ID on profile modification (`PATCH /users/profile/`); always bind updates directly to `request.user.profile` to prevent IDOR.

