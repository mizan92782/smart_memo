---
name: notifications-background-jobs
description: Order notifications, low-stock alerts, asynchronous tasks and reliable event processing.
---
# Notifications and Background Jobs

## Rules
- Keep slow email, SMS, push, report exports and other external work out of latency-sensitive requests when possible.
- Use the project's established queue/task system rather than introducing a second one without justification.
- Define retry, timeout, deduplication and dead-letter/failure handling.
- Do not send notifications before the transaction creating the event is committed.
- Use an outbox or equivalent reliable handoff when losing an event would be unacceptable.
- Make consumers idempotent because jobs and callbacks can be delivered more than once.
- Do not include sensitive data unnecessarily in notification content.
- Track job failures and provide a way to retry safely.

## Acceptance checks
- Duplicate job delivery does not duplicate business effects.
- Failed notification delivery does not roll back a valid order.
- Critical events are not silently lost between database commit and job enqueue.

## Verified Implementation Pattern
- **Idempotent In-App & Email Feed**: `Notification` model with unique `idempotency_key` preventing duplicate alerts on network retry or redundant job delivery.
- **Safe Transactional Boundary**: Notifications and Celery email jobs are enqueued strictly via `transaction.on_commit`, guaranteeing that events are never dispatched for transactions that rolled back.
- **Error Containment**: Email sending failures are safely logged and retried via Celery without blocking or aborting checkout, stock movements, or order status changes.
- **Automated Low-Stock Trigger**: `NotificationService.notify_low_stock_if_needed` inspects `balance.is_low_stock` on every stock deduction or order reservation, instantly notifying the vendor.
- **Tenant & Recipient Isolation**: `NotificationViewSet` scopes queries strictly to `recipient = request.user`. Mutating read status on another user's notification is rejected with 403 Forbidden.

