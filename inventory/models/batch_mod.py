from decimal import Decimal
from django.db import models
from django.utils import timezone
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store
from products.models.product_mod import Product


class BatchStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    NEAR_EXPIRY = 'near_expiry', 'Near Expiry'
    EXPIRED = 'expired', 'Expired'
    DEPLETED = 'depleted', 'Depleted'
    DISPOSED = 'disposed', 'Disposed'


class ProductBatch(BaseModel):
    """
    Perishable product batch with manufacture date, expiry date, FEFO tracking,
    and clearance pricing capability.
    """
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='batches',
        db_index=True
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='batches',
        db_index=True
    )
    batch_number = models.CharField(max_length=64, db_index=True)
    manufacture_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(db_index=True)
    initial_quantity = models.DecimalField(max_digits=10, decimal_places=3)
    current_quantity = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('0.000'))
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(
        max_length=20,
        choices=BatchStatus.choices,
        default=BatchStatus.ACTIVE,
        db_index=True
    )
    is_clearance = models.BooleanField(default=False, db_index=True)
    clearance_discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['expiry_date', 'created_at']
        verbose_name = 'Product Batch'
        verbose_name_plural = 'Product Batches'
        indexes = [
            models.Index(fields=['store', 'product', 'expiry_date']),
            models.Index(fields=['store', 'status', 'expiry_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['store', 'product', 'batch_number'],
                name='unique_store_product_batch'
            ),
            models.CheckConstraint(
                check=models.Q(current_quantity__gte=0),
                name='batch_current_quantity_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(initial_quantity__gt=0),
                name='batch_initial_quantity_positive'
            ),
            models.CheckConstraint(
                check=models.Q(cost_price__gte=0),
                name='batch_cost_price_non_negative'
            ),
            models.CheckConstraint(
                check=models.Q(clearance_discount_percent__gte=0) & models.Q(clearance_discount_percent__lte=100),
                name='batch_clearance_discount_range'
            ),
        ]

    def days_until_expiry(self, reference_date=None) -> int:
        """Returns integer days remaining until expiry from reference_date (defaults to today)."""
        ref = reference_date or timezone.now().date()
        return (self.expiry_date - ref).days

    @property
    def is_expired(self) -> bool:
        """Check if batch is expired relative to current date."""
        return self.days_until_expiry() < 0

    @property
    def clearance_unit_price(self) -> Decimal:
        """Returns price after clearance discount if batch is flagged for clearance."""
        if self.is_clearance and self.clearance_discount_percent > 0:
            multiplier = (Decimal('100.00') - self.clearance_discount_percent) / Decimal('100.00')
            return (self.product.price * multiplier).quantize(Decimal('0.01'))
        return self.product.price

    @property
    def total_valuation(self) -> Decimal:
        """Total inventory value of remaining quantity at cost price."""
        return (self.current_quantity * self.cost_price).quantize(Decimal('0.01'))

    def calculate_effective_status(self, reference_date=None, near_expiry_days: int = 7) -> str:
        """Calculate dynamic status based on current quantity and expiry threshold."""
        if self.status == BatchStatus.DISPOSED:
            return BatchStatus.DISPOSED
        if self.current_quantity <= Decimal('0.000'):
            return BatchStatus.DEPLETED
        days = self.days_until_expiry(reference_date)
        if days < 0:
            return BatchStatus.EXPIRED
        if days <= near_expiry_days:
            return BatchStatus.NEAR_EXPIRY
        return BatchStatus.ACTIVE

    def __str__(self):
        return f"[{self.batch_number}] {self.product.name} (Exp: {self.expiry_date}, Qty: {self.current_quantity})"
