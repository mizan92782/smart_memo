from typing import Optional
from django.db.models import QuerySet
from inventory.models.transfer_mod import StockTransfer, StockTransferItem


class TransferRepository:
    """Handles pure database queries for inter-store stock transfers (static methods only)."""

    @staticmethod
    def get_by_id(transfer_id: int) -> Optional[StockTransfer]:
        return (
            StockTransfer.objects
            .filter(pk=transfer_id, is_deleted=False)
            .select_related('vendor', 'source_store', 'destination_store', 'received_by')
            .prefetch_related('items__source_product', 'items__destination_product')
            .first()
        )

    @staticmethod
    def get_by_transfer_number(number: str) -> Optional[StockTransfer]:
        if not number:
            return None
        return (
            StockTransfer.objects
            .filter(transfer_number=number.strip(), is_deleted=False)
            .select_related('vendor', 'source_store', 'destination_store', 'received_by')
            .prefetch_related('items__source_product', 'items__destination_product')
            .first()
        )

    @staticmethod
    def get_by_vendor(vendor_id: int) -> QuerySet[StockTransfer]:
        return (
            StockTransfer.objects
            .filter(vendor_id=vendor_id, is_deleted=False)
            .select_related('source_store', 'destination_store', 'vendor', 'received_by')
            .prefetch_related('items__source_product')
            .order_by('-created_at')
        )

    @staticmethod
    def get_by_source_store(store_id: int) -> QuerySet[StockTransfer]:
        return (
            StockTransfer.objects
            .filter(source_store_id=store_id, is_deleted=False)
            .select_related('source_store', 'destination_store', 'vendor')
            .prefetch_related('items__source_product')
            .order_by('-created_at')
        )

    @staticmethod
    def get_by_destination_store(store_id: int) -> QuerySet[StockTransfer]:
        return (
            StockTransfer.objects
            .filter(destination_store_id=store_id, is_deleted=False)
            .select_related('source_store', 'destination_store', 'vendor')
            .prefetch_related('items__destination_product')
            .order_by('-created_at')
        )

    @staticmethod
    def create_transfer(**kwargs) -> StockTransfer:
        return StockTransfer.objects.create(**kwargs)

    @staticmethod
    def create_transfer_item(**kwargs) -> StockTransferItem:
        return StockTransferItem.objects.create(**kwargs)
