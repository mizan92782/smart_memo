from typing import Optional
from django.db.models import QuerySet
from orders.models.return_mod import OrderReturn, OrderReturnItem


class ReturnRepository:
    """Handles pure database queries for Order Returns and Return Items (static methods only)."""

    @staticmethod
    def get_by_id(return_id: int) -> Optional[OrderReturn]:
        return (
            OrderReturn.objects
            .filter(pk=return_id, is_deleted=False)
            .select_related('order', 'store', 'customer', 'vendor', 'processed_by')
            .prefetch_related('items__product', 'items__order_item')
            .first()
        )

    @staticmethod
    def get_by_return_number(number: str) -> Optional[OrderReturn]:
        if not number:
            return None
        return (
            OrderReturn.objects
            .filter(return_number=number.strip(), is_deleted=False)
            .select_related('order', 'store', 'customer', 'vendor', 'processed_by')
            .prefetch_related('items__product', 'items__order_item')
            .first()
        )

    @staticmethod
    def get_by_customer(customer_id: int) -> QuerySet[OrderReturn]:
        return (
            OrderReturn.objects
            .filter(customer_id=customer_id, is_deleted=False)
            .select_related('order', 'store', 'customer', 'vendor')
            .prefetch_related('items__product')
            .order_by('-created_at')
        )

    @staticmethod
    def get_by_vendor(vendor_id: int) -> QuerySet[OrderReturn]:
        return (
            OrderReturn.objects
            .filter(vendor_id=vendor_id, is_deleted=False)
            .select_related('order', 'store', 'customer', 'vendor')
            .prefetch_related('items__product')
            .order_by('-created_at')
        )

    @staticmethod
    def get_by_store(store_id: int) -> QuerySet[OrderReturn]:
        return (
            OrderReturn.objects
            .filter(store_id=store_id, is_deleted=False)
            .select_related('order', 'store', 'customer', 'vendor')
            .prefetch_related('items__product')
            .order_by('-created_at')
        )

    @staticmethod
    def get_by_order(order_id: int) -> QuerySet[OrderReturn]:
        return (
            OrderReturn.objects
            .filter(order_id=order_id, is_deleted=False)
            .select_related('order', 'store', 'customer', 'vendor')
            .prefetch_related('items__product')
            .order_by('-created_at')
        )

    @staticmethod
    def create_return(**kwargs) -> OrderReturn:
        return OrderReturn.objects.create(**kwargs)

    @staticmethod
    def create_return_item(**kwargs) -> OrderReturnItem:
        return OrderReturnItem.objects.create(**kwargs)
