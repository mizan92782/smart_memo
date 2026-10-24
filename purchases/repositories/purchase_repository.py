from typing import Optional
from django.db.models import QuerySet
from purchases.models.purchase_mod import Supplier, Purchase, PurchaseItem


class PurchaseRepository:
    """
    Data-access layer for Supplier and Purchase models.
    All methods are static to enforce statelessness.
    """

    @staticmethod
    def get_supplier_by_id(supplier_id: int) -> Optional[Supplier]:
        return Supplier.objects.filter(pk=supplier_id, is_deleted=False).first()

    @staticmethod
    def list_suppliers_for_store(store_id: int) -> QuerySet:
        return Supplier.objects.filter(store_id=store_id, is_deleted=False)

    @staticmethod
    def get_purchase_by_id(purchase_id: int) -> Optional[Purchase]:
        return (
            Purchase.objects
            .filter(pk=purchase_id, is_deleted=False)
            .select_related('store', 'supplier', 'created_by')
            .prefetch_related('items__product')
            .first()
        )

    @staticmethod
    def list_purchases_for_store(store_id: int) -> QuerySet:
        return (
            Purchase.objects
            .filter(store_id=store_id, is_deleted=False)
            .select_related('store', 'supplier', 'created_by')
            .prefetch_related('items__product')
            .order_by('-created_at')
        )
