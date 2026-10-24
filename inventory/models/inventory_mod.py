from decimal import Decimal
from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store
from products.models.product_mod import Product


class StockMovementType(models.TextChoices):
    PURCHASE_RECEIVE = 'purchase_receive', 'Purchase Receive'
    ORDER_RESERVE = 'order_reserve', 'Order Reserve'
    ORDER_FULFILL = 'order_fulfill', 'Order Fulfill'
    ORDER_CANCEL_RESTORE = 'order_cancel_restore', 'Order Cancel Restore'
    MANUAL_ADJUSTMENT = 'manual_adjustment', 'Manual Adjustment'
    DAMAGE_LOSS = 'damage_loss', 'Damage / Loss'
    RETURN = 'return', 'Customer Return'
    RECONCILIATION = 'reconciliation', 'Physical Inventory Reconciliation'


class StockBalance(BaseModel):
    """
    Current stock balance for a product within a store.
    Separates on-hand stock and reserved stock for concurrency-safe ordering.
    """
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='stock_balances'
    )
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_balance'
    )
    on_hand = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('0.000'))
    reserved = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('0.000'))
    low_stock_threshold = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('5.000'))

    class Meta:
        ordering = ['product__name']
        verbose_name = 'Stock Balance'
        verbose_name_plural = 'Stock Balances'
        constraints = [
            models.CheckConstraint(
                check=models.Q(on_hand__gte=0),
                name='stock_on_hand_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(reserved__gte=0),
                name='stock_reserved_non_negative'
            ),
        ]

    @property
    def available(self) -> Decimal:
        """Available stock ready to be sold (on_hand minus reserved)."""
        return max(Decimal('0.000'), self.on_hand - self.reserved)

    @property
    def is_low_stock(self) -> bool:
        return self.available <= self.low_stock_threshold

    def __str__(self):
        return f"{self.product.name} @ {self.store.name}: On Hand={self.on_hand}, Reserved={self.reserved}"


class StockLedgerEntry(BaseModel):
    """
    Append-only stock audit ledger.
    Every change to StockBalance MUST write an immutable ledger entry.
    """
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='stock_ledger_entries'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='ledger_entries'
    )
    movement_type = models.CharField(
        max_length=30,
        choices=StockMovementType.choices
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    balance_after = models.DecimalField(max_digits=10, decimal_places=3)
    reference_id = models.CharField(max_length=100, blank=True, default="")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock Ledger Entry'
        verbose_name_plural = 'Stock Ledger Entries'

    def __str__(self):
        return f"[{self.movement_type}] {self.product.name}: qty={self.quantity} (after={self.balance_after})"
