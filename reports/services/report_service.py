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
