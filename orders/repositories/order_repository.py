from typing import Optional
from django.db.models import QuerySet
from orders.models.order_mod import Order, OrderItem, SalesMemo


class OrderRepository:
    """Handles database queries for Orders and Sales Memos (static methods only)."""

    @staticmethod
    def get_by_id(order_id: int) -> Optional[Order]:
        return Order.objects.filter(pk=order_id, is_deleted=False).prefetch_related('items__product').first()

    @staticmethod
    def get_by_idempotency_key(key: str) -> Optional[Order]:
        if not key:
            return None
        return Order.objects.filter(idempotency_key=key, is_deleted=False).first()

    @staticmethod
    def get_by_customer(customer_id: int) -> QuerySet[Order]:
        return Order.objects.filter(customer_id=customer_id, is_deleted=False).prefetch_related('items__product')

    @staticmethod
    def get_by_store(store_id: int) -> QuerySet[Order]:
        return Order.objects.filter(store_id=store_id, is_deleted=False).prefetch_related('items__product')

    @staticmethod
    def create_order(**kwargs) -> Order:
        return Order.objects.create(**kwargs)

    @staticmethod
    def create_order_item(**kwargs) -> OrderItem:
        return OrderItem.objects.create(**kwargs)

    @staticmethod
    def create_sales_memo(**kwargs) -> SalesMemo:
        return SalesMemo.objects.create(**kwargs)

    @staticmethod
    def update_order(order: Order, **kwargs) -> Order:
        update_fields = []
        for key, value in kwargs.items():
            if hasattr(order, key):
                setattr(order, key, value)
                update_fields.append(key)
        if update_fields:
            if 'updated_at' not in update_fields:
                update_fields.append('updated_at')
            order.save(update_fields=update_fields)
        return order
