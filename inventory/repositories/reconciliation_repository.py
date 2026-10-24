from typing import Optional
from decimal import Decimal
from django.db.models import QuerySet
from inventory.models.reconciliation_mod import (
    StockReconciliation,
    StockReconciliationItem,
    ReconciliationStatus
)
from stores.models.store_mod import Store
from products.models.product_mod import Product


class ReconciliationRepository:
    """Handles database queries and writes for stock reconciliations."""

    @staticmethod
    def create_reconciliation(
        store: Store,
        reconciliation_number: str,
        initiated_by=None,
        notes: str = ""
    ) -> StockReconciliation:
        return StockReconciliation.objects.create(
            store=store,
            reconciliation_number=reconciliation_number,
            initiated_by=initiated_by,
            status=ReconciliationStatus.DRAFT,
            notes=notes
        )

    @staticmethod
    def create_reconciliation_item(
        reconciliation: StockReconciliation,
        product: Product,
        system_stock: Decimal,
        physical_stock: Decimal,
        discrepancy: Decimal,
        unit_cost_snapshot: Decimal,
        variance_value: Decimal,
        notes: str = ""
    ) -> StockReconciliationItem:
        return StockReconciliationItem.objects.create(
            reconciliation=reconciliation,
            product=product,
            system_stock=system_stock,
            physical_stock=physical_stock,
            discrepancy=discrepancy,
            unit_cost_snapshot=unit_cost_snapshot,
            variance_value=variance_value,
            notes=notes
        )

    @staticmethod
    def get_by_id(reconciliation_id: int) -> Optional[StockReconciliation]:
        return StockReconciliation.objects.filter(
            id=reconciliation_id
        ).select_related('store', 'initiated_by', 'applied_by').prefetch_related('items__product').first()

    @staticmethod
    def get_by_store(store_id: int) -> QuerySet[StockReconciliation]:
        return StockReconciliation.objects.filter(
            store_id=store_id
        ).select_related('store', 'initiated_by', 'applied_by').prefetch_related('items__product').order_by('-created_at')

    @staticmethod
    def get_by_stores(store_ids: list[int]) -> QuerySet[StockReconciliation]:
        return StockReconciliation.objects.filter(
            store_id__in=store_ids
        ).select_related('store', 'initiated_by', 'applied_by').prefetch_related('items__product').order_by('-created_at')
