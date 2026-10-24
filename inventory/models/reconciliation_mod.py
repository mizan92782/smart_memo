import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store
from products.models.product_mod import Product


class ReconciliationStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    APPLIED = 'applied', 'Applied'
    CANCELLED = 'cancelled', 'Cancelled'


class StockReconciliation(BaseModel):
    """
    Physical Inventory Count & Batch Stock Reconciliation Session.
    Enables vendors to audit physical stock against system ledger balances,
    compute variances, and atomically post batch adjustments to the stock ledger.
    """
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='stock_reconciliations'
    )
    reconciliation_number = models.CharField(
        max_length=64,
        unique=True,
        db_index=True
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_reconciliations'
    )
    status = models.CharField(
        max_length=20,
        choices=ReconciliationStatus.choices,
        default=ReconciliationStatus.DRAFT,
        db_index=True
    )
    notes = models.TextField(blank=True, default='')
    total_items_counted = models.IntegerField(default=0)
    total_discrepancy_qty = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal('0.000')
    )
    total_discrepancy_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    applied_at = models.DateTimeField(null=True, blank=True)
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applied_reconciliations'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock Reconciliation'
        verbose_name_plural = 'Stock Reconciliations'

    def __str__(self):
        return f"{self.reconciliation_number} ({self.store.name}) [{self.status}]"


class StockReconciliationItem(BaseModel):
    """
    Individual product count entry within a reconciliation session.
    Records system stock snapshot, counted physical stock, and calculated variance.
    """
    reconciliation = models.ForeignKey(
        StockReconciliation,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reconciliation_items'
    )
    system_stock = models.DecimalField(max_digits=10, decimal_places=3)
    physical_stock = models.DecimalField(max_digits=10, decimal_places=3)
    discrepancy = models.DecimalField(max_digits=10, decimal_places=3)  # physical_stock - system_stock
    unit_cost_snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    variance_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['product__name']
        verbose_name = 'Stock Reconciliation Item'
        verbose_name_plural = 'Stock Reconciliation Items'
        unique_together = ('reconciliation', 'product')

    def __str__(self):
        return f"{self.product.name}: Sys={self.system_stock}, Phys={self.physical_stock}, Diff={self.discrepancy}"
