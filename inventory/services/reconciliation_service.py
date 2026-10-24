import uuid
from decimal import Decimal
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.utils import timezone

from inventory.models.inventory_mod import StockBalance, StockMovementType
from inventory.models.reconciliation_mod import (
    StockReconciliation,
    StockReconciliationItem,
    ReconciliationStatus
)
from inventory.repositories.inventory_repository import InventoryRepository
from inventory.repositories.reconciliation_repository import ReconciliationRepository
from stores.models.store_mod import Store
from products.models.product_mod import Product
from audit.services.audit_service import AuditService
from audit.models.audit_mod import AuditAction
from notifications.services.notification_service import NotificationService
from shared.caching.cache_service import CacheService


class ReconciliationService:
    """
    Business service orchestrating physical inventory counts, variance computation,
    and atomic batch reconciliation into stock ledger balances.
    """

    @staticmethod
    @transaction.atomic
    def create_reconciliation(
        store: Store,
        actor,
        items_data: List[Dict[str, Any]],
        notes: str = ""
    ) -> StockReconciliation:
        """
        Initiates a physical inventory reconciliation draft session.
        Snapshots system stock, records physical count, and calculates discrepancies.
        """
        if not items_data:
            raise ValueError("Reconciliation requires at least one counted product item.")

        rec_number = f"REC-{store.id}-{uuid.uuid4().hex[:8].upper()}"
        reconciliation = ReconciliationRepository.create_reconciliation(
            store=store,
            reconciliation_number=rec_number,
            initiated_by=actor,
            notes=notes
        )

        total_discrepancy_qty = Decimal('0.000')
        total_discrepancy_val = Decimal('0.00')
        counted_count = 0

        # Avoid duplicate products in the same session
        seen_product_ids = set()

        for item in items_data:
            product_id = item.get('product_id')
            if not product_id:
                raise ValueError("Each reconciliation item must specify product_id.")
            if product_id in seen_product_ids:
                raise ValueError(f"Duplicate product_id {product_id} in reconciliation batch.")
            seen_product_ids.add(product_id)

            product = Product.objects.filter(
                id=product_id,
                store=store,
                is_deleted=False
            ).first()
            if not product:
                raise ValueError(f"Product ID {product_id} not found in store '{store.name}'.")

            try:
                phys_stock = Decimal(str(item.get('physical_stock', 0)))
            except (ValueError, TypeError):
                raise ValueError(f"Invalid physical stock quantity for product '{product.name}'.")

            if phys_stock < Decimal('0.000'):
                raise ValueError(f"Physical stock cannot be negative for product '{product.name}'.")

            # Acquire or initialize current balance
            balance = InventoryRepository.get_or_create_balance(store, product)
            system_stock = balance.on_hand
            discrepancy = phys_stock - system_stock
            unit_cost = product.effective_price
            variance_value = discrepancy * unit_cost
            item_notes = item.get('notes', '')

            ReconciliationRepository.create_reconciliation_item(
                reconciliation=reconciliation,
                product=product,
                system_stock=system_stock,
                physical_stock=phys_stock,
                discrepancy=discrepancy,
                unit_cost_snapshot=unit_cost,
                variance_value=variance_value,
                notes=item_notes
            )

            total_discrepancy_qty += discrepancy
            total_discrepancy_val += variance_value
            counted_count += 1

        reconciliation.total_items_counted = counted_count
        reconciliation.total_discrepancy_qty = total_discrepancy_qty
        reconciliation.total_discrepancy_value = total_discrepancy_val
        reconciliation.save(update_fields=[
            'total_items_counted',
            'total_discrepancy_qty',
            'total_discrepancy_value',
            'updated_at'
        ])

        return reconciliation

    @staticmethod
    @transaction.atomic
    def apply_reconciliation(
        reconciliation_id: int,
        actor
    ) -> StockReconciliation:
        """
        Atomically commits physical stock counts to inventory balances and ledger.
        Enforces that stock on hand never drops below reserved active orders.
        """
        reconciliation = StockReconciliation.objects.select_for_update().filter(id=reconciliation_id).first()
        if not reconciliation:
            raise ValueError("Reconciliation session not found.")

        if reconciliation.status != ReconciliationStatus.DRAFT:
            raise ValueError(f"Cannot apply reconciliation in '{reconciliation.status}' status. Only draft can be applied.")

        # Check authorization
        if actor and reconciliation.store.vendor != actor and not actor.is_superuser:
            raise PermissionError("You do not have permission to apply reconciliation for this store.")

        items = list(reconciliation.items.select_related('product').all())

        # Sort products to prevent deadlock across concurrent operations
        items.sort(key=lambda x: x.product_id)

        for item in items:
            product = item.product
            balance = StockBalance.objects.select_for_update().get(store=reconciliation.store, product=product)

            new_on_hand = balance.on_hand + item.discrepancy
            if new_on_hand < balance.reserved:
                raise ValueError(
                    f"Reconciling '{product.name}' would reduce on-hand ({new_on_hand}) below reserved orders ({balance.reserved})."
                )

            if item.discrepancy != Decimal('0.000'):
                balance.on_hand = new_on_hand
                balance.save(update_fields=['on_hand', 'updated_at'])

                # Synchronize read-model product.stock
                product.stock = balance.on_hand
                product.save(update_fields=['stock', 'updated_at'])

                # Record immutable audit ledger entry
                InventoryRepository.log_ledger_entry(
                    store=reconciliation.store,
                    product=product,
                    movement_type=StockMovementType.RECONCILIATION,
                    quantity=item.discrepancy,
                    balance_after=balance.on_hand,
                    reference_id=reconciliation.reconciliation_number,
                    actor=actor,
                    notes=item.notes or f"Physical audit variance adjustment ({reconciliation.reconciliation_number})"
                )

                # Low-stock alerting
                NotificationService.notify_low_stock_if_needed(reconciliation.store, product, balance)

        reconciliation.status = ReconciliationStatus.APPLIED
        reconciliation.applied_at = timezone.now()
        reconciliation.applied_by = actor
        reconciliation.save(update_fields=['status', 'applied_at', 'applied_by', 'updated_at'])

        # Invalidate cached catalog for this store
        CacheService.invalidate_catalog(reconciliation.store.id)

        # Log platform activity trail
        AuditService.log(
            action=AuditAction.INVENTORY_RECONCILED,
            target_model="StockReconciliation",
            target_id=reconciliation.id,
            actor=actor,
            store=reconciliation.store,
            details={
                "reconciliation_number": reconciliation.reconciliation_number,
                "items_counted": reconciliation.total_items_counted,
                "net_variance_qty": str(reconciliation.total_discrepancy_qty),
                "net_variance_value": str(reconciliation.total_discrepancy_value)
            }
        )

        return reconciliation

    @staticmethod
    @transaction.atomic
    def cancel_reconciliation(
        reconciliation_id: int,
        actor
    ) -> StockReconciliation:
        """Cancels a draft reconciliation without modifying inventory balances."""
        reconciliation = StockReconciliation.objects.select_for_update().filter(id=reconciliation_id).first()
        if not reconciliation:
            raise ValueError("Reconciliation session not found.")

        if reconciliation.status != ReconciliationStatus.DRAFT:
            raise ValueError(f"Cannot cancel reconciliation in '{reconciliation.status}' status. Only draft can be cancelled.")

        if actor and reconciliation.store.vendor != actor and not actor.is_superuser:
            raise PermissionError("You do not have permission to cancel reconciliation for this store.")

        reconciliation.status = ReconciliationStatus.CANCELLED
        reconciliation.save(update_fields=['status', 'updated_at'])
        return reconciliation
