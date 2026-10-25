import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store
from products.models.product_mod import Product


class TransferStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    IN_TRANSIT = 'in_transit', 'In Transit'
    RECEIVED = 'received', 'Received'
    CANCELLED = 'cancelled', 'Cancelled'


class StockTransfer(BaseModel):
    """
    Formal inter-store inventory transfer between stores owned by the same vendor.
    """
    transfer_number = models.CharField(max_length=64, unique=True, blank=True)
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stock_transfers'
    )
    source_store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='outgoing_transfers'
    )
    destination_store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='incoming_transfers'
    )
    status = models.CharField(
        max_length=20,
        choices=TransferStatus.choices,
        default=TransferStatus.DRAFT
    )
    driver_name = models.CharField(max_length=100, blank=True, default='')
    driver_phone = models.CharField(max_length=30, blank=True, default='')
    vehicle_type = models.CharField(max_length=50, blank=True, default='')
    tracking_notes = models.TextField(blank=True, default='')
    dispatched_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='received_stock_transfers'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock Transfer'
        verbose_name_plural = 'Stock Transfers'

    def save(self, *args, **kwargs):
        if not self.transfer_number:
            self.transfer_number = f"TRF-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    @property
    def total_quantity(self) -> Decimal:
        return sum((item.quantity for item in self.items.all()), Decimal('0.000'))

    def format_waybill_thermal(self, width: int = 40) -> str:
        """
        Formats transfer manifest / dispatch waybill into a 40-col monospace slip.
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

        lines.append("=" * w)
        lines.append(center("INTER-STORE STOCK TRANSFER"))
        lines.append(center("TRANSFER MANIFEST / WAYBILL"))
        lines.append("=" * w)

        lines.append(row("Transfer #:", self.transfer_number))
        date_str = self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else ""
        if date_str:
            lines.append(row("Created:", date_str))
        lines.append(row("Status:", self.get_status_display()))
        lines.append("-" * w)
        lines.append(f"FROM: {self.source_store.name.upper()}"[:w])
        lines.append(f"TO:   {self.destination_store.name.upper()}"[:w])
        lines.append("-" * w)


        if self.driver_name:
            lines.append(row("Driver:", self.driver_name[:max(0, w - 9)]))
        if self.driver_phone:
            lines.append(row("Phone:", self.driver_phone))
        if self.vehicle_type:
            lines.append(row("Vehicle:", self.vehicle_type))
        if self.dispatched_at:
            lines.append(row("Dispatched:", self.dispatched_at.strftime('%Y-%m-%d %H:%M')))
        if self.received_at:
            lines.append(row("Received:", self.received_at.strftime('%Y-%m-%d %H:%M')))

        lines.append("-" * w)
        lines.append(row("PRODUCT ITEM", "TRANSFER QTY"))
        lines.append("-" * w)

        for item in self.items.all():
            name = item.product_name_snapshot[:w]
            lines.append(name)
            qty_str = f"{item.quantity:.3f}"
            if item.received_quantity is not None:
                qty_str += f" (Rcvd: {item.received_quantity:.3f})"
            lines.append(row("  Qty:", qty_str))

        lines.append("-" * w)
        lines.append(row("TOTAL ITEMS:", str(self.items.count())))
        lines.append(row("TOTAL UNITS:", f"{self.total_quantity:.3f}"))
        lines.append("-" * w)

        if self.tracking_notes:
            lines.append(f"Notes: {self.tracking_notes}"[:w])
            lines.append("-" * w)

        lines.append(center("Driver Signature: ________________"))
        lines.append(center("Receiver Signature: ______________"))
        lines.append("=" * w)

        return "\n".join(lines)

    def __str__(self):
        return f"{self.transfer_number}: {self.source_store.name} -> {self.destination_store.name} ({self.status})"


class StockTransferItem(BaseModel):
    """
    Individual line item and quantity transferred between stores.
    """
    transfer = models.ForeignKey(
        StockTransfer,
        on_delete=models.CASCADE,
        related_name='items'
    )
    source_product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='transfer_items_out'
    )
    destination_product = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='transfer_items_in'
    )
    product_name_snapshot = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    received_quantity = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)

    class Meta:
        verbose_name = 'Stock Transfer Item'
        verbose_name_plural = 'Stock Transfer Items'

    def __str__(self):
        return f"{self.product_name_snapshot} x {self.quantity} in {self.transfer.transfer_number}"
