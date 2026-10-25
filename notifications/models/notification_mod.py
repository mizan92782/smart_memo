from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store


class NotificationType(models.TextChoices):
    ORDER_SUBMITTED = 'order_submitted', 'Order Submitted'
    ORDER_ACCEPTED = 'order_accepted', 'Order Accepted'
    ORDER_PREPARING = 'order_preparing', 'Order Preparing'
    ORDER_READY_FOR_PICKUP = 'order_ready_for_pickup', 'Ready for Pickup'
    ORDER_OUT_FOR_DELIVERY = 'order_out_for_delivery', 'Out for Delivery'
    ORDER_COMPLETED = 'order_completed', 'Order Completed'
    ORDER_CANCELLED = 'order_cancelled', 'Order Cancelled'
    ORDER_RETURN_REQUESTED = 'order_return_requested', 'Order Return Requested'
    ORDER_RETURN_PROCESSED = 'order_return_processed', 'Order Return Processed'
    LOW_STOCK_ALERT = 'low_stock_alert', 'Low Stock Alert'
    PURCHASE_RECEIVED = 'purchase_received', 'Purchase Received'
    STOCK_TRANSFER_DISPATCHED = 'stock_transfer_dispatched', 'Stock Transfer Dispatched'
    STOCK_TRANSFER_RECEIVED = 'stock_transfer_received', 'Stock Transfer Received'
    SYSTEM = 'system', 'System Notification'



class Notification(BaseModel):
    """
    In-app and async notification entity.
    Supports tenant-scoping via store link, read/unread states, and idempotency deduplication.
    """
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(
        max_length=128,
        unique=True,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', '-created_at']),
        ]

    def __str__(self):
        status = "Read" if self.is_read else "Unread"
        return f"[{self.notification_type}] {self.title} -> {self.recipient.email} ({status})"
