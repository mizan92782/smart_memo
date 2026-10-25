from django.db import models
from django.conf import settings
from rest_framework.exceptions import PermissionDenied


class AuditAction:
    """Standardized action identifiers for audit log entries."""
    STORE_VERIFIED = "STORE_VERIFIED"
    STORE_SUSPENDED = "STORE_SUSPENDED"
    STORE_ACTIVATED = "STORE_ACTIVATED"
    INVENTORY_ADJUSTED = "INVENTORY_ADJUSTED"
    INVENTORY_RECONCILED = "INVENTORY_RECONCILED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_PAYMENT_COLLECTED = "ORDER_PAYMENT_COLLECTED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    STOCK_RECEIVED = "STOCK_RECEIVED"
    ORDER_RETURN_REQUESTED = "ORDER_RETURN_REQUESTED"
    ORDER_RETURN_PROCESSED = "ORDER_RETURN_PROCESSED"
    STOCK_TRANSFER_DISPATCHED = "STOCK_TRANSFER_DISPATCHED"
    STOCK_TRANSFER_RECEIVED = "STOCK_TRANSFER_RECEIVED"
    STOCK_TRANSFER_CANCELLED = "STOCK_TRANSFER_CANCELLED"
    BATCH_CREATED = "BATCH_CREATED"
    BATCH_DISPOSED = "BATCH_DISPOSED"
    BATCH_CLEARANCE = "BATCH_CLEARANCE"



class AuditLog(models.Model):
    """
    Immutable audit trail for all critical business, security, and financial operations.
    Enforces tenant isolation by linking to the relevant store where applicable.
    """
    store = models.ForeignKey(
        'stores.Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        db_index=True
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        db_index=True
    )
    actor_email = models.CharField(max_length=255, blank=True, default='')
    actor_role = models.CharField(max_length=50, blank=True, default='')
    action = models.CharField(max_length=100, db_index=True)
    target_model = models.CharField(max_length=100, db_index=True)
    target_id = models.CharField(max_length=100, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['store', 'action', '-created_at']),
            models.Index(fields=['actor', '-created_at']),
            models.Index(fields=['target_model', 'target_id']),
        ]

    def __str__(self):
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {self.action} on {self.target_model}:{self.target_id} by {self.actor_email or 'System'}"

    def save(self, *args, **kwargs):
        """Audit records are append-only. Modification of existing records is strictly rejected."""
        if self.pk is not None:
            raise PermissionDenied("Audit log entries are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Audit records cannot be deleted."""
        raise PermissionDenied("Audit log entries cannot be deleted.")
