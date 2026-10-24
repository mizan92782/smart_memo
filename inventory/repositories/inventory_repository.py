from typing import Optional
from decimal import Decimal
from django.db.models import QuerySet
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry, StockMovementType
from stores.models.store_mod import Store
from products.models.product_mod import Product


class InventoryRepository:
    """Handles all database operations for inventory balances and audit ledger."""

    @staticmethod
    def get_or_create_balance(store: Store, product: Product) -> StockBalance:
        balance, _ = StockBalance.objects.get_or_create(
            store=store,
            product=product,
            defaults={'on_hand': Decimal('0.000'), 'reserved': Decimal('0.000')}
        )
        return balance

    @staticmethod
    def get_by_store(store_id: int) -> QuerySet[StockBalance]:
        return StockBalance.objects.filter(store_id=store_id).select_related('product', 'store')

    @staticmethod
    def get_ledger_entries(store_id: int, product_id: Optional[int] = None) -> QuerySet[StockLedgerEntry]:
        qs = StockLedgerEntry.objects.filter(store_id=store_id).select_related('product', 'actor')
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs.order_by('-created_at')

    @staticmethod
    def log_ledger_entry(
        store: Store,
        product: Product,
        movement_type: str,
        quantity: Decimal,
        balance_after: Decimal,
        reference_id: str = "",
        actor=None,
        notes: str = ""
    ) -> StockLedgerEntry:
        return StockLedgerEntry.objects.create(
            store=store,
            product=product,
            movement_type=movement_type,
            quantity=quantity,
            balance_after=balance_after,
            reference_id=reference_id,
            actor=actor,
            notes=notes
        )
