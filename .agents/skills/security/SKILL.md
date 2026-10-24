---
name: security
description: General application security, input validation, secrets, uploads and abuse controls.
---
# Application Security

## Rules
- Validate inputs on the server and use explicit schemas/allowlists.
- Use parameterized queries or safe ORM operations.
- Protect against mass assignment by accepting only explicitly allowed fields.
- Enforce object-level authorization for every read and write.
- Use secure secret management and environment variables; never commit secrets.
- Configure CORS, cookies/tokens, HTTPS, CSRF protections and security headers appropriately for the chosen architecture.
- Rate-limit authentication, search, memo submission, exports and other abuse-prone operations.
- Validate uploaded file type, size, content and storage access.
- Avoid leaking stack traces, SQL, credentials, private tenant information or personal data in errors/logs.
- Keep dependencies updated and run available security checks.
- Treat third-party API payloads and uploaded content as untrusted.

## Acceptance checks
- Authorization and validation failures are tested.
- No secrets are committed or returned.
- Sensitive operations are rate-limited and audited where appropriate.
