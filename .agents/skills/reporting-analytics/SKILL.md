---
name: reporting-analytics
description: Vendor sales, purchase, inventory, revenue and order reports.
---
# Reporting and Analytics

## Rules
- Every vendor report must be scoped to stores the actor is authorized to access.
- Define metrics precisely: gross sales, discounts, refunds, delivery charges, tax, net sales, collected payments and outstanding COD are not interchangeable.
- Define the date timezone and inclusive/exclusive range behavior.
- Use database aggregation rather than loading all rows into application memory.
- Paginate detailed records and bound report date ranges.
- Use background jobs for expensive exports or long-running reports.
- Cache only if invalidation/freshness behavior is explicit.
- Do not expose purchase costs or profit margins to customers.
- Ensure cancelled, refunded and incomplete orders are handled consistently.

## Acceptance checks
- Totals reconcile with underlying orders, payments and refunds.
- Cross-tenant report access is blocked.
- Date boundaries, timezone and cancellation cases are tested.

## Verified Architecture Patterns
- Execute SQL aggregations using Django `aggregate(Sum(...), Count(...), Coalesce(...))` with conditional `Q()` filters instead of in-memory python loops.
- Separate completed sales from pending and cancelled orders (`gross_sales` only counts `status=COMPLETED`).
- Explicitly split COD collected (`payment_status=COLLECTED`) from outstanding COD (`payment_status=PENDING` on active orders).
- Filter stock health via `StockBalance.available <= low_stock_threshold` to generate realtime low-stock alerts without background queue delays.
- Enforce store ownership check: `store.vendor == request.user` returning 403 Forbidden on foreign store IDs.
- **Excel-Compatible CSV Export Engine**: `ExportService` streams accounting sales & tax, inventory valuation, procurement history, and perishable batch reports with UTF-8 BOM encoding (`\ufeff`) to prevent character distortion across spreadsheet applications. Strict tenant boundaries verify store ownership before dispatching attachment downloads.
