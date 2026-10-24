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
    def get_by_vendor(vendor_id: int) -> QuerySet[Order]:
        return Order.objects.filter(vendor_id=vendor_id, is_deleted=False).prefetch_related('items__product')

    @staticmethod
    def get_by_store(store_id: int) -> QuerySet[Order]:
        return Order.objects.filter(store_id=store_id, is_deleted=False).prefetch_related('items__product')

    @staticmethod
    def get_by_walk_in_code(code: str, store_id: Optional[int] = None, vendor_id: Optional[int] = None) -> Optional[Order]:
        """Fetch order by in-store counter walk-in verification code."""
        if not code:
            return None
        qs = Order.objects.filter(
            walk_in_code=code.strip(),
            is_deleted=False
        ).select_related('customer', 'vendor', 'store').prefetch_related('items__product')
        if store_id is not None:
            qs = qs.filter(store_id=store_id)
        if vendor_id is not None:
            qs = qs.filter(vendor_id=vendor_id)
        return qs.order_by('-created_at').first()

    @staticmethod
    def create_order(**kwargs) -> Order:
        if 'store' in kwargs and 'vendor' not in kwargs:
            kwargs['vendor'] = kwargs['store'].vendor
        return Order.objects.create(**kwargs)

    @staticmethod
    def create_order_item(**kwargs) -> OrderItem:
        return OrderItem.objects.create(**kwargs)

    @staticmethod
    def create_sales_memo(**kwargs) -> SalesMemo:
        if 'order' in kwargs:
            order = kwargs['order']
            if 'customer' not in kwargs:
                kwargs['customer'] = order.customer
            if 'vendor' not in kwargs:
                kwargs['vendor'] = getattr(order, 'vendor', None) or (order.store.vendor if order.store else None)
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

    @staticmethod
    def get_sales_memos(
        customer_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
        store_id: Optional[int] = None,
        from_date=None,
        to_date=None,
        search: Optional[str] = None
    ) -> QuerySet[SalesMemo]:
        """Fetch sales memos with optional customer, vendor, store, date and search filters."""
        qs = SalesMemo.objects.filter(is_deleted=False).select_related('order', 'customer', 'vendor', 'order__store')
        if customer_id is not None:
            qs = qs.filter(customer_id=customer_id)
        if vendor_id is not None:
            qs = qs.filter(vendor_id=vendor_id)
        if store_id is not None:
            qs = qs.filter(order__store_id=store_id)
        if from_date:
            qs = qs.filter(created_at__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__lte=to_date)
        if search and search.strip():
            s = search.strip()
            from django.db.models import Q
            qs = qs.filter(
                Q(memo_number__icontains=s) |
                Q(order__order_number__icontains=s) |
                Q(store_name_snapshot__icontains=s) |
                Q(walk_in_code_snapshot__icontains=s)
            )
        return qs.order_by('-created_at')

    @staticmethod
    def get_customer_spending_summary(customer_id: int) -> dict:
        """
        Database aggregation of customer spending across all stores.
        Returns total spent, total saved, memo count, and store breakdown.
        """
        from django.db.models import Sum, Count, Max
        from django.db.models.functions import Coalesce
        from decimal import Decimal

        base_qs = SalesMemo.objects.filter(customer_id=customer_id, is_deleted=False)

        aggregates = base_qs.aggregate(
            total_spent=Coalesce(Sum('amount_paid'), Decimal('0.00')),
            total_saved=Coalesce(Sum('discount_amount'), Decimal('0.00')),
            total_memos=Count('id')
        )

        store_stats = (
            base_qs.values('order__store_id', 'store_name_snapshot')
            .annotate(
                memo_count=Count('id'),
                total_spent=Coalesce(Sum('amount_paid'), Decimal('0.00')),
                last_visit=Max('created_at')
            )
            .order_by('-total_spent')
        )

        store_breakdown = [
            {
                'store_id': s['order__store_id'],
                'store_name': s['store_name_snapshot'],
                'memo_count': s['memo_count'],
                'total_spent': str(s['total_spent']),
                'last_visit': s['last_visit'].isoformat() if s['last_visit'] else None
            }
            for s in store_stats
        ]

        return {
            'total_spent': str(aggregates['total_spent']),
            'total_saved': str(aggregates['total_saved']),
            'total_memos': aggregates['total_memos'],
            'stores_visited_count': len(store_breakdown),
            'store_breakdown': store_breakdown
        }
