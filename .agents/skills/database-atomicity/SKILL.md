---
name: database-atomicity
description: Transaction boundaries, constraints, concurrency, idempotency and rollback.
---
# Database Atomicity and Concurrency

## Use when
Changing inventory, purchases, order submission, cancellation, fulfillment, payment, returns, or any operation spanning multiple records.

## Rules
- Identify the invariant before coding (e.g. available stock must not become negative).
- Put related database writes inside one transaction.
- Use database constraints as the final line of defense where possible.
- Use row locks, optimistic concurrency, or conditional atomic updates appropriate to the database.
- Lock resources in a consistent order to reduce deadlocks.
- Keep external network calls out of long-running database transactions; use an outbox/job pattern where needed.
- Make retries safe with idempotency keys or unique operation references.
- Roll back all related changes when a critical step fails.
- Handle deadlocks/serialization failures with bounded, safe retries only when the operation is idempotent.
- Do not claim concurrency safety based solely on a single-threaded unit test.

## Required scenarios
- Two customers order the last unit simultaneously.
- A purchase receipt is submitted twice.
- An order is cancelled while fulfillment is starting.
- A payment/delivery callback is delivered more than once.
- A failure occurs after one write but before the next.

## Acceptance checks
- Invariants hold under concurrent requests.
- Rollbacks leave no partial business operation.
- Duplicate requests/events do not duplicate stock, sales or payments.
