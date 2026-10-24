import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store
from products.models.product_mod import Product


class OrderStatus(models.TextChoices):
    SUBMITTED = 'submitted', 'Submitted'
    ACCEPTED = 'accepted', 'Accepted'
    PREPARING = 'preparing', 'Preparing'
    READY_FOR_PICKUP = 'ready_for_pickup', 'Ready for Pickup'
    OUT_FOR_DELIVERY = 'out_for_delivery', 'Out for Delivery'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'
    REJECTED = 'rejected', 'Rejected'


class FulfillmentType(models.TextChoices):
    PICKUP = 'pickup', 'Pickup'
    DELIVERY = 'delivery', 'Home Delivery'
    WALK_IN = 'walk_in', 'In-Store Walk-In Handover'


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    COLLECTED = 'collected', 'Collected'
    FAILED = 'failed', 'Failed'
    REFUNDED = 'refunded', 'Refunded'


class PaymentMethod(models.TextChoices):
    COD = 'cod', 'Cash on Delivery'


class Order(BaseModel):
    """Customer order submitted to a specific store."""
    order_number = models.CharField(max_length=64, unique=True, blank=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vendor_orders'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='orders'
    )
    status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.SUBMITTED
    )
    fulfillment_type = models.CharField(
        max_length=20,
        choices=FulfillmentType.choices,
        default=FulfillmentType.PICKUP
    )
    delivery_address = models.TextField(blank=True, default="")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon_code = models.CharField(max_length=32, blank=True, default="")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.COD
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    idempotency_key = models.CharField(max_length=128, unique=True, null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    accepted_at = models.DateTimeField(null=True, blank=True)
    preparing_at = models.DateTimeField(null=True, blank=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='collected_orders'
    )
    customer_phone_snapshot = models.CharField(max_length=30, blank=True, default="")

    # Delivery Driver Assignment & Dispatch
    delivery_person_name = models.CharField(max_length=100, blank=True, default="")
    delivery_person_phone = models.CharField(max_length=30, blank=True, default="")
    delivery_vehicle_type = models.CharField(max_length=50, blank=True, default="")
    delivery_tracking_notes = models.TextField(blank=True, default="")
    delivery_assigned_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)

    # In-Store Counter POS Walk-In Verification Code
    walk_in_code = models.CharField(max_length=12, blank=True, db_index=True)


    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    @property
    def user(self):
        return self.customer

    @user.setter
    def user(self, value):
        self.customer = value

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
        if not self.walk_in_code and self.fulfillment_type in [FulfillmentType.WALK_IN, FulfillmentType.PICKUP]:
            import secrets
            self.walk_in_code = f"{secrets.randbelow(900000) + 100000}"
        if self.store_id and not self.vendor_id:
            if hasattr(self, 'store') and self.store and self.store.vendor:
                self.vendor = self.store.vendor
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
            if 'vendor' not in update_fields and self.vendor_id:
                update_fields.add('vendor')
            if 'walk_in_code' not in update_fields and self.walk_in_code:
                update_fields.add('walk_in_code')
            kwargs['update_fields'] = update_fields
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} ({self.store.name} - {self.status})"


class OrderItem(BaseModel):
    """Snapshot of a purchased product item in an order."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items'
    )
    product_name_snapshot = models.CharField(max_length=200)
    unit_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.product_name_snapshot} x {self.quantity} in {self.order.order_number}"


class SalesMemo(BaseModel):
    """Finalized immutable receipt of a completed order sale."""
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='sales_memo'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sales_memos'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vendor_sales_memos'
    )
    memo_number = models.CharField(max_length=64, unique=True, blank=True)
    store_name_snapshot = models.CharField(max_length=200)
    customer_email_snapshot = models.CharField(max_length=200)
    items_snapshot = models.JSONField(default=list)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon_code = models.CharField(max_length=32, blank=True, default="")
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    walk_in_code_snapshot = models.CharField(max_length=12, blank=True, default="")

    class Meta:
        verbose_name = 'Sales Memo'
        verbose_name_plural = 'Sales Memos'

    @property
    def user(self):
        return self.customer

    @user.setter
    def user(self, value):
        self.customer = value

    def save(self, *args, **kwargs):
        if not self.memo_number:
            self.memo_number = f"MEMO-{uuid.uuid4().hex[:10].upper()}"
        if self.order_id:
            if not self.customer_id and hasattr(self, 'order') and self.order:
                self.customer = self.order.customer
            if not self.vendor_id and hasattr(self, 'order') and self.order:
                self.vendor = getattr(self.order, 'vendor', None) or (self.order.store.vendor if self.order.store else None)
            if not self.walk_in_code_snapshot and hasattr(self, 'order') and self.order:
                self.walk_in_code_snapshot = getattr(self.order, 'walk_in_code', '')
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
            if 'customer' not in update_fields and self.customer_id:
                update_fields.add('customer')
            if 'vendor' not in update_fields and self.vendor_id:
                update_fields.add('vendor')
            if 'walk_in_code_snapshot' not in update_fields and self.walk_in_code_snapshot:
                update_fields.add('walk_in_code_snapshot')
            kwargs['update_fields'] = update_fields
        super().save(*args, **kwargs)

    def format_thermal_receipt(self, width: int = 40) -> str:
        """
        Formats this sales memo into a clean, 40-column monospace thermal receipt slip.
        Suitable for 58mm / 80mm POS thermal printers and mobile/terminal receipt rendering.
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

        # Header
        lines.append("=" * w)
        lines.append(center(self.store_name_snapshot.upper()))
        lines.append(center("Smart Memo System - Digital Receipt"))
        lines.append("=" * w)

        created_str = self.created_at.strftime('%Y-%m-%d %H:%M UTC') if self.created_at else ""
        if created_str:
            lines.append(row("Date:", created_str))
        lines.append(row("Memo #:", self.memo_number))
        if hasattr(self, 'order') and self.order:
            lines.append(row("Order #:", getattr(self.order, 'order_number', '')))
        if self.customer_email_snapshot:
            lines.append(row("Customer:", self.customer_email_snapshot[:max(0, w - 11)]))
        if self.walk_in_code_snapshot:
            lines.append(row("Walk-In Code:", self.walk_in_code_snapshot))

        lines.append("-" * w)
        lines.append(row("ITEM", "QTY x PRICE   TOTAL"))
        lines.append("-" * w)

        # Items
        for item in self.items_snapshot or []:
            name = item.get('product_name', 'Item')
            qty = str(item.get('quantity', '1'))
            price = str(item.get('unit_price', '0.00'))
            total = str(item.get('line_total', '0.00'))

            lines.append(name[:w])
            calc_str = f"{qty} x {price}"
            lines.append(row(f"  {calc_str}", total))

        lines.append("-" * w)
        lines.append(row("Subtotal:", f"{self.subtotal:.2f}"))

        if self.discount_amount and self.discount_amount > 0:
            coupon_label = f"Discount ({self.coupon_code}):" if self.coupon_code else "Discount:"
            lines.append(row(coupon_label, f"-{self.discount_amount:.2f}"))

        if self.delivery_fee and self.delivery_fee > 0:
            lines.append(row("Delivery Fee:", f"{self.delivery_fee:.2f}"))

        lines.append("-" * w)
        lines.append(row("TOTAL AMOUNT:", f"{self.total_amount:.2f}"))
        lines.append(row("AMOUNT PAID:", f"{self.amount_paid:.2f}"))
        lines.append("-" * w)

        lines.append(center("Thank you for shopping with us!"))
        lines.append(center("Keep this memo for your records"))
        lines.append("=" * w)

        return "\n".join(lines)

    def __str__(self):
        return f"{self.memo_number} for {self.order.order_number}"
