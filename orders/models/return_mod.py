import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store
from products.models.product_mod import Product
from orders.models.order_mod import Order, OrderItem


class ReturnStatus(models.TextChoices):
    REQUESTED = 'requested', 'Requested'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    COMPLETED = 'completed', 'Completed'


class ReturnReason(models.TextChoices):
    DAMAGED_DEFECTIVE = 'damaged_defective', 'Damaged / Defective'
    EXPIRED = 'expired', 'Expired'
    WRONG_PRODUCT = 'wrong_product', 'Wrong Product'
    NOT_AS_DESCRIBED = 'not_as_described', 'Not As Described'
    CUSTOMER_CHANGED_MIND = 'customer_changed_mind', 'Customer Changed Mind'
    OTHER = 'other', 'Other'


class OrderReturn(BaseModel):
    """
    Formal return request and financial credit note for items returned from a completed order.
    """
    return_number = models.CharField(max_length=64, unique=True, blank=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='returns'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='order_returns'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='customer_returns'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vendor_returns'
    )
    status = models.CharField(
        max_length=20,
        choices=ReturnStatus.choices,
        default=ReturnStatus.REQUESTED
    )
    reason = models.CharField(
        max_length=30,
        choices=ReturnReason.choices,
        default=ReturnReason.DAMAGED_DEFECTIVE
    )
    reason_notes = models.TextField(blank=True, default="")
    rejection_reason = models.TextField(blank=True, default="")
    total_refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    restock_inventory = models.BooleanField(default=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_returns'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    items_snapshot = models.JSONField(default=list, blank=True)
    loyalty_points_deducted = models.PositiveIntegerField(default=0)
    loyalty_stamps_deducted = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order Return'
        verbose_name_plural = 'Order Returns'

    def save(self, *args, **kwargs):
        if not self.return_number:
            self.return_number = f"RET-{uuid.uuid4().hex[:10].upper()}"
        if self.store_id and not self.vendor_id:
            if hasattr(self, 'store') and self.store and self.store.vendor:
                self.vendor = self.store.vendor
        super().save(*args, **kwargs)

    def format_credit_note_thermal(self, width: int = 40) -> str:
        """
        Formats this return / credit note into a 40-column monospace slip for thermal printers.
        """
        w = max(32, width)
        lines = []

        def center(text: str) -> str:
            return text[:w].center(w)

        def row(left: str, right: str) -> str:
            space = w - len(left) - len(right)
            if space < 1:
                space = 1
                left = left[:max(0, w - len(right) - 1)]
            return f"{left}{' ' * space}{right}"

        store_name = self.store.name if self.store else "STORE"
        lines.append("=" * w)
        lines.append(center(store_name.upper()))
        lines.append(center("CREDIT NOTE / RETURN RECEIPT"))
        lines.append("=" * w)

        date_str = self.created_at.strftime('%Y-%m-%d %H:%M UTC') if self.created_at else ""
        if date_str:
            lines.append(row("Date:", date_str))
        lines.append(row("Return #:", self.return_number))
        lines.append(row("Order #:", self.order.order_number if self.order else ""))
        customer_email = self.customer.email if self.customer else ""
        if customer_email:
            lines.append(row("Customer:", customer_email[:max(0, w - 11)]))
        lines.append(row("Status:", self.get_status_display()))
        lines.append(row("Reason:", self.get_reason_display()))
        lines.append(row("Restocked:", "Yes" if self.restock_inventory else "No (Damage/Waste)"))

        lines.append("-" * w)
        lines.append(row("ITEM", "QTY x REFUND   TOTAL"))
        lines.append("-" * w)

        items = self.items_snapshot or []
        if not items and hasattr(self, 'items'):
            items = [
                {
                    'product_name': item.product_name_snapshot,
                    'quantity': str(item.quantity),
                    'unit_price': str(item.unit_price),
                    'refund_subtotal': str(item.refund_subtotal),
                }
                for item in self.items.all()
            ]

        for item in items:
            name = item.get('product_name', 'Item')
            qty = str(item.get('quantity', '1'))
            price = str(item.get('unit_price', '0.00'))
            subtotal = str(item.get('refund_subtotal', '0.00'))
            lines.append(name[:w])
            calc_str = f"{qty} x {price}"
            lines.append(row(f"  {calc_str}", f"-{subtotal}"))

        lines.append("-" * w)
        lines.append(row("TOTAL REFUND:", f"-{self.total_refund_amount:.2f}"))
        if self.loyalty_points_deducted and self.loyalty_points_deducted > 0:
            lines.append(row("Points Adjusted:", f"-{self.loyalty_points_deducted} pts"))
        if self.loyalty_stamps_deducted and self.loyalty_stamps_deducted > 0:
            lines.append(row("Stamps Adjusted:", f"-{self.loyalty_stamps_deducted} stamp"))
        lines.append("-" * w)

        lines.append(center("Refund processed successfully"))
        lines.append(center("Keep this slip for your accounting records"))
        lines.append("=" * w)

        return "\n".join(lines)

    def __str__(self):
        return f"{self.return_number} for {self.order.order_number} ({self.status})"


class OrderReturnItem(BaseModel):
    """
    Individual product line item returned within an OrderReturn.
    """
    order_return = models.ForeignKey(
        OrderReturn,
        on_delete=models.CASCADE,
        related_name='items'
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        related_name='return_items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='returned_items'
    )
    product_name_snapshot = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    refund_subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Order Return Item'
        verbose_name_plural = 'Order Return Items'

    def __str__(self):
        return f"{self.product_name_snapshot} x {self.quantity} in {self.order_return.return_number}"
