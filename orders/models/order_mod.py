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


    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
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

    class Meta:
        verbose_name = 'Sales Memo'
        verbose_name_plural = 'Sales Memos'

    def save(self, *args, **kwargs):
        if not self.memo_number:
            self.memo_number = f"MEMO-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.memo_number} for {self.order.order_number}"
