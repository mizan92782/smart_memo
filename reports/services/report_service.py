from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import date
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import Coalesce
from stores.models.store_mod import Store
from orders.models.order_mod import Order, OrderStatus, PaymentStatus
from inventory.models.inventory_mod import StockBalance
from purchases.models.purchase_mod import Purchase, PurchaseStatus


class ReportService:
    """
    Reporting and analytics service providing database-aggregated metrics
    strictly isolated to vendor-owned stores.
    """

    @staticmethod
    def get_sales_report(
        store: Store,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Aggregate sales performance, order counts, gross revenue, and COD status."""
        qs = Order.objects.filter(store=store, is_deleted=False)
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        zero_dec = Decimal('0.00')

        metrics = qs.aggregate(
            total_orders=Count('id'),
            completed_orders=Count('id', filter=Q(status=OrderStatus.COMPLETED)),
            cancelled_orders=Count('id', filter=Q(status=OrderStatus.CANCELLED)),
            rejected_orders=Count('id', filter=Q(status=OrderStatus.REJECTED)),
            gross_sales=Coalesce(
                Sum('total_amount', filter=Q(status=OrderStatus.COMPLETED)),
                zero_dec
            ),
            net_product_sales=Coalesce(
                Sum('subtotal', filter=Q(status=OrderStatus.COMPLETED)),
                zero_dec
            ),
            delivery_fees_collected=Coalesce(
                Sum('delivery_fee', filter=Q(status=OrderStatus.COMPLETED)),
                zero_dec
            ),
            cod_collected=Coalesce(
                Sum('total_amount', filter=Q(payment_status=PaymentStatus.COLLECTED)),
                zero_dec
            ),
            cod_outstanding=Coalesce(
                Sum(
                    'total_amount',
                    filter=Q(
                        payment_status=PaymentStatus.PENDING,
                        status__in=[
                            OrderStatus.SUBMITTED,
                            OrderStatus.ACCEPTED,
                            OrderStatus.PREPARING,
                            OrderStatus.READY_FOR_PICKUP,
                            OrderStatus.OUT_FOR_DELIVERY
                        ]
                    )
                ),
                zero_dec
            )
        )

        return {
            "store_id": store.id,
            "store_name": store.name,
            "period": {
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
            },
            "orders": {
                "total": metrics['total_orders'],
                "completed": metrics['completed_orders'],
                "cancelled": metrics['cancelled_orders'],
                "rejected": metrics['rejected_orders'],
            },
            "financials": {
                "gross_sales": str(metrics['gross_sales']),
                "net_product_sales": str(metrics['net_product_sales']),
                "delivery_fees_collected": str(metrics['delivery_fees_collected']),
                "cod_collected": str(metrics['cod_collected']),
                "cod_outstanding": str(metrics['cod_outstanding']),
            }
        }

    @staticmethod
    def get_inventory_report(store: Store) -> Dict[str, Any]:
        """Aggregate stock health, low-stock alerts, and out-of-stock items."""
        balances = (
            StockBalance.objects
            .filter(store=store, is_deleted=False)
            .select_related('product')
        )

        total_tracked_products = balances.count()
        low_stock_list = []
        out_of_stock_count = 0

        for b in balances:
            avail = b.available
            if avail <= Decimal('0.000'):
                out_of_stock_count += 1

            if b.is_low_stock:
                low_stock_list.append({
                    "product_id": b.product.id,
                    "product_name": b.product.name,
                    "sku": b.product.sku,
                    "on_hand": str(b.on_hand),
                    "reserved": str(b.reserved),
                    "available": str(avail),
                    "threshold": str(b.low_stock_threshold)
                })

        return {
            "store_id": store.id,
            "store_name": store.name,
            "total_tracked_products": total_tracked_products,
            "out_of_stock_count": out_of_stock_count,
            "low_stock_count": len(low_stock_list),
            "low_stock_items": low_stock_list
        }

    @staticmethod
    def get_purchases_report(
        store: Store,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Aggregate procurement spending, purchase order volumes, and supplier breakdown."""
        qs = Purchase.objects.filter(store=store, is_deleted=False)
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        zero_dec = Decimal('0.00')

        metrics = qs.aggregate(
            total_purchases=Count('id'),
            received_purchases=Count('id', filter=Q(status=PurchaseStatus.RECEIVED)),
            cancelled_purchases=Count('id', filter=Q(status=PurchaseStatus.CANCELLED)),
            total_procurement_cost=Coalesce(
                Sum('total_cost', filter=Q(status=PurchaseStatus.RECEIVED)),
                zero_dec
            )
        )

        return {
            "store_id": store.id,
            "store_name": store.name,
            "period": {
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
            },
            "purchases": {
                "total": metrics['total_purchases'],
                "received": metrics['received_purchases'],
                "cancelled": metrics['cancelled_purchases'],
            },
            "financials": {
                "total_procurement_cost": str(metrics['total_procurement_cost']),
            }
        }

    @staticmethod
    def get_hot_products(store: Store, limit: int = 12) -> list:
        from orders.models.order_mod import OrderItem
        from products.models.product_mod import Product
        from products.models.product_image_mod import ProductImage

        sales_agg = (
            OrderItem.objects
            .filter(order__store=store)
            .values('product_id')
            .annotate(
                units_sold=Sum('quantity'),
                gross_revenue=Sum('line_total')
            )
            .order_by('-units_sold')
        )
        sales_dict = {item['product_id']: item for item in sales_agg if item['product_id']}

        products = Product.objects.filter(store=store, is_deleted=False).select_related('category')
        results = []
        for p in products:
            info = sales_dict.get(p.id, {'units_sold': 0, 'gross_revenue': Decimal('0.00')})
            img = ProductImage.objects.filter(product=p, is_primary=True).first() or ProductImage.objects.filter(product=p).first()
            img_url = img.effective_url if img else ""
            results.append({
                "id": p.id,
                "name": p.name,
                "category_name": p.category.name if p.category else "General",
                "barcode": p.barcode or p.sku or "",
                "sku": p.sku or "",
                "aisle": p.aisle or "",
                "shelf_location": p.shelf_location or "",
                "price": str(p.price),
                "cost_price": str(p.cost_price),
                "units_sold": info['units_sold'],
                "gross_revenue": str(info['gross_revenue']),
                "image_url": img_url,
                "measure": p.measure,
                "unit": p.unit,
            })

        results.sort(key=lambda x: (x['units_sold'], Decimal(x['gross_revenue'])), reverse=True)
        return results[:limit]

    @staticmethod
    def get_category_sales_report(
        store: Store,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Aggregate sales performance by product category for a store.
        Returns category breakdown, units sold, gross sales revenue,
        order count, and percentage contribution to overall store sales.
        """
        from orders.models.order_mod import OrderItem, OrderStatus
        from categories.models.category_mod import Category

        items_qs = OrderItem.objects.filter(
            order__store=store,
            order__status=OrderStatus.COMPLETED,
            order__is_deleted=False
        )
        if start_date:
            items_qs = items_qs.filter(order__created_at__date__gte=start_date)
        if end_date:
            items_qs = items_qs.filter(order__created_at__date__lte=end_date)

        cat_aggregates = (
            items_qs
            .values('product__category_id', 'product__category__name')
            .annotate(
                units_sold=Coalesce(Sum('quantity'), Decimal('0.000')),
                gross_sales=Coalesce(Sum('line_total'), Decimal('0.00')),
                order_count=Count('order_id', distinct=True),
                product_count=Count('product_id', distinct=True)
            )
        )

        sales_map = {}
        total_gross = Decimal('0.00')
        total_units = Decimal('0.000')

        for row in cat_aggregates:
            cid = row['product__category_id']
            cname = row['product__category__name'] or 'General'
            u_sold = row['units_sold']
            g_sales = row['gross_sales']
            sales_map[cid] = {
                'category_id': cid,
                'category_name': cname,
                'units_sold': float(u_sold),
                'gross_sales': g_sales,
                'order_count': row['order_count'],
                'product_count': row['product_count'],
            }
            total_gross += g_sales
            total_units += u_sold

        # Ensure all existing categories of this store are represented (even with 0 sales)
        all_categories = Category.objects.filter(store=store, is_deleted=False)
        for cat in all_categories:
            if cat.id not in sales_map:
                prod_count = cat.products.filter(is_deleted=False).count()
                sales_map[cat.id] = {
                    'category_id': cat.id,
                    'category_name': cat.name,
                    'units_sold': 0.0,
                    'gross_sales': Decimal('0.00'),
                    'order_count': 0,
                    'product_count': prod_count,
                }

        results = list(sales_map.values())
        # Sort by gross_sales descending, then units_sold descending
        results.sort(key=lambda x: (x['gross_sales'], x['units_sold']), reverse=True)

        # Compute percentages
        for item in results:
            if total_gross > Decimal('0.00'):
                pct = round((item['gross_sales'] / total_gross) * 100, 1)
            else:
                pct = 0.0
            item['percentage'] = float(pct)
            item['gross_sales'] = str(item['gross_sales'])

        return {
            "store_id": store.id,
            "store_name": store.name,
            "period": {
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
            },
            "total_gross_sales": str(total_gross),
            "total_units_sold": float(total_units),
            "categories": results
        }

    @staticmethod
    def get_sales_trends(
        store: Store,
        days: int = 14
    ) -> Dict[str, Any]:
        """
        Aggregate daily sales trends (revenue, order counts, units)
        over the specified number of days for charting and visualization.
        """
        from datetime import timedelta
        from django.utils import timezone
        from orders.models.order_mod import Order, OrderStatus, OrderItem

        today = timezone.now().date()
        start_date = today - timedelta(days=days - 1)

        orders = (
            Order.objects
            .filter(
                store=store,
                status=OrderStatus.COMPLETED,
                is_deleted=False,
                created_at__date__gte=start_date,
                created_at__date__lte=today
            )
            .values('created_at__date')
            .annotate(
                gross_sales=Coalesce(Sum('total_amount'), Decimal('0.00')),
                order_count=Count('id')
            )
        )
        orders_by_date = {row['created_at__date']: row for row in orders}

        # Daily units sold
        items = (
            OrderItem.objects
            .filter(
                order__store=store,
                order__status=OrderStatus.COMPLETED,
                order__is_deleted=False,
                order__created_at__date__gte=start_date,
                order__created_at__date__lte=today
            )
            .values('order__created_at__date')
            .annotate(units_sold=Coalesce(Sum('quantity'), Decimal('0.000')))
        )
        items_by_date = {row['order__created_at__date']: row['units_sold'] for row in items}

        trend_data = []
        for i in range(days):
            current_day = start_date + timedelta(days=i)
            ord_row = orders_by_date.get(current_day, {})
            u_sold = items_by_date.get(current_day, Decimal('0.000'))
            trend_data.append({
                "date": current_day.isoformat(),
                "label": current_day.strftime("%b %d"),
                "gross_sales": str(ord_row.get('gross_sales', Decimal('0.00'))),
                "order_count": ord_row.get('order_count', 0),
                "units_sold": float(u_sold),
            })

        return {
            "store_id": store.id,
            "days": days,
            "start_date": start_date.isoformat(),
            "end_date": today.isoformat(),
            "trends": trend_data
        }

