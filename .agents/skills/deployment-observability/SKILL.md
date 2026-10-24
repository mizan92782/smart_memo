---
name: deployment-observability
description: Environment configuration, migrations, health checks, logs, monitoring and production readiness.
---
# Deployment and Observability

## Rules
- Inspect existing deployment target and project conventions before changing configuration.
- Separate development, test and production settings.
- Keep secrets outside source control.
- Make database migrations repeatable and review destructive changes carefully.
- Provide health/readiness checks appropriate to the deployment architecture.
- Use structured logs with request/correlation IDs where possible.
- Never log passwords, tokens, payment secrets or unnecessary personal information.
- Monitor error rates, latency, database saturation, background jobs and cache health.
- Define backup and restore expectations for production data.
- Use a safe rollout/rollback plan for schema changes.
- Run tests and migrations checks before deployment; do not claim deployment success without evidence.

## Acceptance checks
- Setup and deployment steps are documented.
- Health checks do not expose secrets.
- Migration and rollback risks are understood.
- Logs help diagnose failures without exposing sensitive data.

## Health & Probes Architecture
- `/health/`: Dual-mode endpoint (HTML dashboard by default; JSON system metrics if requested via `Accept: application/json` or `?format=json`).
- `/health/live/`: Lightweight liveness probe returning HTTP 200 `{"status": "alive"}` for process container checks.
- `/health/ready/`: Deep readiness probe checking:
  1. PostgreSQL database connectivity (`SELECT 1`).
  2. Database migration state via `MigrationExecutor` (`executor.migration_plan`).
  3. Redis / local memory cache set/get verification.
  - Returns HTTP 200 when ready; HTTP 503 Service Unavailable when any critical downstream dependency is down.
  - Zero sensitive connection parameters or credentials exposed in payloads.

