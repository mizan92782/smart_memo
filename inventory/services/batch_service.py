from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import date
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from inventory.models.batch_mod import ProductBatch, BatchStatus
from inventory.models.inventory_mod import StockBalance, StockMovementType
from inventory.repositories.batch_repository import BatchRepository
from inventory.repositories.inventory_repository import InventoryRepository
from inventory.services.inventory_service import InventoryService
from stores.models.store_mod import Store
from products.models.product_mod import Product
from audit.services.audit_service import AuditService
from audit.models.audit_mod import AuditAction
from notifications.models.notification_mod import NotificationType
from shared.caching.cache_service import CacheService


class BatchService:
    """
    Business domain service for perishable batch lifecycle:
    FEFO allocation, stock intake, clearance pricing, spoilage write-offs, and near-expiry alerting.
    """

    @staticmethod
    @transaction.atomic
    def create_batch(
        store: Store,
        product: Product,
        batch_number: str,
        expiry_date: date,
        initial_quantity: Decimal,
        cost_price: Decimal = Decimal('0.00'),
        manufacture_date: Optional[date] = None,
        add_to_stock: bool = False,
        actor=None,
        notes: str = ""
    ) -> ProductBatch:
        """Register a new batch for a store product with optional stock balance intake."""
        batch_number = (batch_number or "").strip()
        if not batch_number:
            raise ValidationError({"batch_number": "Batch number cannot be empty."})

        if product.store_id != store.id:
            raise ValidationError({"product": "Product does not belong to the specified store."})

        today = timezone.now().date()
        if expiry_date < today:
            raise ValidationError({"expiry_date": "Expiry date cannot be in the past."})

        if manufacture_date and manufacture_date > expiry_date:
            raise ValidationError({"manufacture_date": "Manufacture date cannot be after expiry date."})

        init_qty = Decimal(str(initial_quantity))
        if init_qty <= Decimal('0.000'):
            raise ValidationError({"initial_quantity": "Initial quantity must be strictly positive."})

        c_price = Decimal(str(cost_price))
        if c_price < Decimal('0.00'):
            raise ValidationError({"cost_price": "Cost price cannot be negative."})

        if ProductBatch.objects.filter(store=store, product=product, batch_number=batch_number).exists():
            raise ValidationError({"batch_number": f"Batch '{batch_number}' already exists for this product in this store."})

        batch = ProductBatch.objects.create(
            store=store,
            product=product,
            batch_number=batch_number,
            manufacture_date=manufacture_date,
            expiry_date=expiry_date,
            initial_quantity=init_qty,
            current_quantity=init_qty,
            cost_price=c_price,
            status=BatchStatus.ACTIVE,
            notes=notes
        )

        if add_to_stock:
            InventoryService.receive_stock(
                store=store,
                product=product,
                quantity=init_qty,
                reference_id=f"BATCH-{batch.batch_number}",
                actor=actor,
                notes=f"Perishable batch {batch_number} stock intake."
            )

        AuditService.log(
            action=AuditAction.BATCH_CREATED,
            target_model="ProductBatch",
            target_id=str(batch.id),
            actor=actor,
            store=store,
            details={
                "batch_number": batch.batch_number,
                "product_id": str(product.id),
                "expiry_date": str(expiry_date),
                "initial_quantity": str(init_qty),
                "cost_price": str(c_price),
                "add_to_stock": add_to_stock,
            }
        )

        return batch

    @staticmethod
    @transaction.atomic
    def allocate_fefo(
        store: Store,
        product: Product,
        quantity: Decimal,
        reference_date: Optional[date] = None,
        deduct: bool = True
    ) -> Dict[str, Any]:
        """
        Allocate requested quantity from batches in FEFO order (earliest expiry first).
        If deduct is True, decrements batch current_quantity and updates depleted status.
        """
        qty_needed = Decimal(str(quantity))
        if qty_needed <= Decimal('0.000'):
            raise ValidationError({"quantity": "Requested allocation quantity must be strictly positive."})

        candidates = list(
            BatchRepository.get_fefo_candidates(
                store=store,
                product=product,
                reference_date=reference_date,
                lock=True
            )
        )

        total_batch_stock = sum((b.current_quantity for b in candidates), Decimal('0.000'))
        if total_batch_stock < qty_needed:
            raise ValidationError(
                f"Insufficient unexpired batch stock for '{product.name}'. "
                f"Requested: {qty_needed}, Available in batches: {total_batch_stock}"
            )

        remaining = qty_needed
        allocations = []

        for batch in candidates:
            if remaining <= Decimal('0.000'):
                break

            alloc_qty = min(remaining, batch.current_quantity)
            if deduct:
                batch.current_quantity -= alloc_qty
                if batch.current_quantity == Decimal('0.000'):
                    batch.status = BatchStatus.DEPLETED
                batch.save(update_fields=['current_quantity', 'status', 'updated_at'])

            allocations.append({
                "batch_id": batch.id,
                "batch_number": batch.batch_number,
                "expiry_date": str(batch.expiry_date),
                "days_until_expiry": batch.days_until_expiry(reference_date),
                "allocated_quantity": str(alloc_qty),
                "cost_price": str(batch.cost_price),
                "current_quantity_remaining": str(batch.current_quantity)
            })

            remaining -= alloc_qty

        return {
            "store_id": store.id,
            "product_id": product.id,
            "product_name": product.name,
            "requested_quantity": str(qty_needed),
            "allocated_quantity": str(qty_needed),
            "deducted": deduct,
            "allocations": allocations
        }

    @staticmethod
    @transaction.atomic
    def dispose_batch(
        batch_id: int,
        quantity: Optional[Decimal] = None,
        reason: str = "Expired / Spoilage",
        actor=None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Atomically write off spoiled or expired batch stock.
        Decrements batch quantity, decreases store StockBalance.on_hand,
        writes an immutable StockMovementType.BATCH_DISPOSAL ledger entry,
        invalidates catalog caches, and logs an immutable audit event.
        """
        batch = BatchRepository.get_by_id(batch_id=batch_id, lock=True)
        if not batch:
            raise ValidationError("Batch not found.")

        if batch.status == BatchStatus.DISPOSED or batch.current_quantity <= Decimal('0.000'):
            raise ValidationError("Batch is already completely disposed or depleted.")

        dispose_qty = Decimal(str(quantity)) if quantity is not None else batch.current_quantity
        if dispose_qty <= Decimal('0.000'):
            raise ValidationError({"quantity": "Disposal quantity must be strictly positive."})

        if dispose_qty > batch.current_quantity:
            raise ValidationError({
                "quantity": f"Cannot dispose {dispose_qty} units; batch only contains {batch.current_quantity} units."
            })

        # Decrement batch quantity
        batch.current_quantity -= dispose_qty
        if batch.current_quantity == Decimal('0.000'):
            batch.status = BatchStatus.DISPOSED
        batch.save(update_fields=['current_quantity', 'status', 'updated_at'])

        # Atomically decrement StockBalance
        InventoryRepository.get_or_create_balance(batch.store, batch.product)
        balance = StockBalance.objects.select_for_update().get(store=batch.store, product=batch.product)

        new_on_hand = balance.on_hand - dispose_qty
        if new_on_hand < balance.reserved:
            raise ValidationError(
                f"Disposal of {dispose_qty} units would breach ongoing customer reservations ({balance.reserved}). "
                f"Current on-hand: {balance.on_hand}"
            )

        balance.on_hand = new_on_hand
        balance.save(update_fields=['on_hand', 'updated_at'])

        batch.product.stock = balance.on_hand
        batch.product.save(update_fields=['stock', 'updated_at'])

        # Write immutable stock ledger entry
        ledger_entry = InventoryRepository.log_ledger_entry(
            store=batch.store,
            product=batch.product,
            movement_type=StockMovementType.BATCH_DISPOSAL,
            quantity=-dispose_qty,
            balance_after=balance.on_hand,
            reference_id=f"DISPOSE-BATCH-{batch.batch_number}",
            actor=actor,
            notes=f"Disposal ({reason}): {notes}".strip()
        )

        # Invalidate tenant catalog cache
        CacheService.invalidate_catalog(batch.store_id)

        # Append immutable audit entry
        AuditService.log(
            action=AuditAction.BATCH_DISPOSED,
            target_model="ProductBatch",
            target_id=str(batch.id),
            actor=actor,
            store=batch.store,
            details={
                "batch_number": batch.batch_number,
                "product_id": str(batch.product_id),
                "disposed_quantity": str(dispose_qty),
                "remaining_batch_quantity": str(batch.current_quantity),
                "financial_loss": str((dispose_qty * batch.cost_price).quantize(Decimal('0.01'))),
                "reason": reason,
                "notes": notes,
                "ledger_entry_id": ledger_entry.id
            }
        )

        return {
            "batch_id": batch.id,
            "batch_number": batch.batch_number,
            "disposed_quantity": str(dispose_qty),
            "remaining_batch_quantity": str(batch.current_quantity),
            "new_store_on_hand": str(balance.on_hand),
            "status": batch.status,
            "financial_loss": str((dispose_qty * batch.cost_price).quantize(Decimal('0.01'))),
            "reason": reason
        }

    @staticmethod
    @transaction.atomic
    def set_clearance(
        batch_id: int,
        discount_percent: Decimal,
        actor=None
    ) -> ProductBatch:
        """Mark batch for clearance discount or remove clearance."""
        batch = BatchRepository.get_by_id(batch_id=batch_id, lock=True)
        if not batch:
            raise ValidationError("Batch not found.")

        pct = Decimal(str(discount_percent))
        if pct < Decimal('0.00') or pct > Decimal('100.00'):
            raise ValidationError({"discount_percent": "Clearance discount must be between 0.00% and 100.00%."})

        batch.is_clearance = (pct > Decimal('0.00'))
        batch.clearance_discount_percent = pct
        batch.save(update_fields=['is_clearance', 'clearance_discount_percent', 'updated_at'])

        AuditService.log(
            action=AuditAction.BATCH_CLEARANCE,
            target_model="ProductBatch",
            target_id=str(batch.id),
            actor=actor,
            store=batch.store,
            details={
                "batch_number": batch.batch_number,
                "is_clearance": batch.is_clearance,
                "discount_percent": str(pct),
                "clearance_price": str(batch.clearance_unit_price)
            }
        )

        return batch

    @staticmethod
    @transaction.atomic
    def scan_and_alert_expiring_batches(
        store: Store,
        days_threshold: int = 7,
        reference_date: Optional[date] = None,
        actor=None
    ) -> List[Dict[str, Any]]:
        """
        Scan store batches, update effective status (NEAR_EXPIRY or EXPIRED),
        and trigger notification alert to store vendor if expiring stock exists.
        """
        ref_date = reference_date or timezone.now().date()
        active_batches = ProductBatch.objects.filter(
            store=store,
            current_quantity__gt=Decimal('0.000')
        ).exclude(
            status=BatchStatus.DISPOSED
        ).select_related('product')

        alert_list = []
        updated_count = 0

        for b in active_batches:
            new_status = b.calculate_effective_status(reference_date=ref_date, near_expiry_days=days_threshold)
            if b.status != new_status:
                b.status = new_status
                b.save(update_fields=['status', 'updated_at'])
                updated_count += 1

            if new_status in (BatchStatus.NEAR_EXPIRY, BatchStatus.EXPIRED):
                alert_list.append({
                    "batch_id": b.id,
                    "batch_number": b.batch_number,
                    "product_id": b.product_id,
                    "product_name": b.product.name,
                    "status": b.status,
                    "expiry_date": str(b.expiry_date),
                    "days_remaining": b.days_until_expiry(ref_date),
                    "current_quantity": str(b.current_quantity),
                    "total_valuation": str(b.total_valuation),
                    "is_clearance": b.is_clearance,
                    "clearance_unit_price": str(b.clearance_unit_price)
                })

        # Trigger notification alert if batches are nearing expiry or expired
        if alert_list:
            from notifications.services.notification_service import NotificationService
            NotificationService.create_notification(
                recipient=store.vendor,
                store=store,
                title="Perishable Stock Expiry Alert",
                message=(
                    f"{len(alert_list)} perishable batch(es) in store '{store.name}' are expired or "
                    f"expiring within {days_threshold} days. Consider clearance discounts or disposal."
                ),
                notification_type=NotificationType.BATCH_EXPIRY_ALERT,
                metadata={
                    "store_id": store.id,
                    "days_threshold": days_threshold,
                    "expiring_batches_count": len(alert_list),
                }
            )

        return alert_list
