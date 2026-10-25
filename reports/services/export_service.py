import csv
import io
from decimal import Decimal
from typing import Optional
from datetime import date
from django.http import HttpResponse
from django.utils import timezone

from stores.models.store_mod import Store
from orders.models.order_mod import Order
from inventory.models.inventory_mod import StockBalance
from inventory.models.batch_mod import ProductBatch
from purchases.models.purchase_mod import Purchase


class ExportService:
    """
    Engine for generating accounting, tax, inventory valuation, and procurement
    CSV / Excel-compatible exports with strict tenant scoping and UTF-8 BOM encoding.
    """

    @staticmethod
    def export_sales_tax_csv(
        store: Store,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> HttpResponse:
        """Export store orders for accounting, revenue recognition, and sales tax reporting."""
        qs = (
            Order.objects
            .filter(store=store, is_deleted=False)
            .select_related('customer')
            .order_by('-created_at')
        )
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        output = io.StringIO()
        # Write UTF-8 BOM so Excel opens non-ASCII characters without encoding errors
        output.write('\ufeff')
        writer = csv.writer(output)

        # Header Row
        writer.writerow([
            "Order Number",
            "Order Date",
            "Customer Email",
            "Order Status",
            "Payment Method",
            "Payment Status",
            "Subtotal",
            "Discount Amount",
            "Delivery Fee",
            "Total Amount",
            "Estimated Tax (5%)"
        ])

        tax_rate = Decimal('0.05')

        for order in qs:
            subtotal = order.subtotal or Decimal('0.00')
            discount = order.discount_amount or Decimal('0.00')
            delivery_fee = order.delivery_fee or Decimal('0.00')
            total = order.total_amount or Decimal('0.00')
            est_tax = (subtotal * tax_rate).quantize(Decimal('0.01'))

            writer.writerow([
                order.order_number,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.customer.email if order.customer else "Guest / Walk-In",
                order.get_status_display() if hasattr(order, 'get_status_display') else order.status,
                order.get_payment_method_display() if hasattr(order, 'get_payment_method_display') else order.payment_method,
                order.get_payment_status_display() if hasattr(order, 'get_payment_status_display') else order.payment_status,
                f"{subtotal:.2f}",
                f"{discount:.2f}",
                f"{delivery_fee:.2f}",
                f"{total:.2f}",
                f"{est_tax:.2f}"
            ])

        date_suffix = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"sales_tax_export_store_{store.id}_{date_suffix}.csv"

        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def export_inventory_valuation_csv(store: Store) -> HttpResponse:
        """Export store product inventory valuation and stock levels."""
        balances = (
            StockBalance.objects
            .filter(store=store, is_deleted=False)
            .select_related('product', 'product__category')
            .order_by('product__name')
        )

        output = io.StringIO()
        output.write('\ufeff')
        writer = csv.writer(output)

        writer.writerow([
            "SKU",
            "Barcode",
            "Product Name",
            "Category",
            "Unit",
            "On Hand",
            "Reserved",
            "Available",
            "Unit Cost Price",
            "Unit Selling Price",
            "Total Cost Value",
            "Potential Retail Value",
            "Low Stock Threshold",
            "Stock Status"
        ])

        for b in balances:
            prod = b.product
            cost_price = prod.cost_price if hasattr(prod, 'cost_price') and prod.cost_price else Decimal('0.00')
            selling_price = prod.price or Decimal('0.00')
            total_cost_val = (b.on_hand * cost_price).quantize(Decimal('0.01'))
            potential_retail_val = (b.on_hand * selling_price).quantize(Decimal('0.01'))

            avail = b.available
            if avail <= Decimal('0.000'):
                stock_status = "Out of Stock"
            elif b.is_low_stock:
                stock_status = "Low Stock"
            else:
                stock_status = "In Stock"

            writer.writerow([
                prod.sku or "N/A",
                prod.barcode or "N/A",
                prod.name,
                prod.category.name if prod.category else "Uncategorized",
                prod.unit or "Unit",
                f"{b.on_hand:.3f}",
                f"{b.reserved:.3f}",
                f"{avail:.3f}",
                f"{cost_price:.2f}",
                f"{selling_price:.2f}",
                f"{total_cost_val:.2f}",
                f"{potential_retail_val:.2f}",
                f"{b.low_stock_threshold:.3f}",
                stock_status
            ])

        date_suffix = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"inventory_valuation_store_{store.id}_{date_suffix}.csv"

        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def export_purchases_procurement_csv(
        store: Store,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> HttpResponse:
        """Export procurement history and accounts payable purchase records."""
        qs = (
            Purchase.objects
            .filter(store=store, is_deleted=False)
            .select_related('supplier', 'created_by')
            .prefetch_related('items')
            .order_by('-created_at')
        )
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        output = io.StringIO()
        output.write('\ufeff')
        writer = csv.writer(output)

        writer.writerow([
            "PO Number",
            "Supplier Name",
            "Supplier Tax ID",
            "Order Date",
            "Received Date",
            "Status",
            "Items Count",
            "Subtotal",
            "Additional Charges",
            "Total Procurement Cost",
            "Reference"
        ])

        for po in qs:
            items_count = po.items.count()
            writer.writerow([
                po.purchase_number,
                po.supplier.name if po.supplier else "N/A",
                po.supplier.tax_id if po.supplier and po.supplier.tax_id else "N/A",
                po.order_date.strftime('%Y-%m-%d') if po.order_date else "",
                po.received_date.strftime('%Y-%m-%d %H:%M:%S') if po.received_date else "Not Received",
                po.get_status_display() if hasattr(po, 'get_status_display') else po.status,
                items_count,
                f"{po.subtotal:.2f}",
                f"{po.additional_charges:.2f}",
                f"{po.total_cost:.2f}",
                po.reference or "N/A"
            ])

        date_suffix = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"purchases_procurement_store_{store.id}_{date_suffix}.csv"

        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @staticmethod
    def export_perishable_batches_csv(store: Store) -> HttpResponse:
        """Export perishable batches, expiry dates, valuations, and clearance states."""
        batches = (
            ProductBatch.objects
            .filter(store=store, is_deleted=False)
            .select_related('product')
            .order_by('expiry_date', 'created_at')
        )

        output = io.StringIO()
        output.write('\ufeff')
        writer = csv.writer(output)

        writer.writerow([
            "Batch Number",
            "SKU",
            "Product Name",
            "Manufacture Date",
            "Expiry Date",
            "Days Remaining",
            "Initial Quantity",
            "Current Quantity",
            "Unit Cost Price",
            "Total Valuation",
            "Status",
            "Is Clearance",
            "Clearance Discount (%)",
            "Clearance Unit Price"
        ])

        for b in batches:
            writer.writerow([
                b.batch_number,
                b.product.sku or "N/A",
                b.product.name,
                b.manufacture_date.strftime('%Y-%m-%d') if b.manufacture_date else "N/A",
                b.expiry_date.strftime('%Y-%m-%d'),
                b.days_until_expiry(),
                f"{b.initial_quantity:.3f}",
                f"{b.current_quantity:.3f}",
                f"{b.cost_price:.2f}",
                f"{b.total_valuation:.2f}",
                b.get_status_display() if hasattr(b, 'get_status_display') else b.status,
                "YES" if b.is_clearance else "NO",
                f"{b.clearance_discount_percent:.2f}",
                f"{b.clearance_unit_price:.2f}"
            ])

        date_suffix = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"perishable_batches_store_{store.id}_{date_suffix}.csv"

        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
