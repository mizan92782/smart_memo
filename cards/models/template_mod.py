from decimal import Decimal
from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.models.card_mod import ShoppingMode


class StoreMemoTemplate(BaseModel):
    """
    Customer-defined routine shopping basket template scoped to a specific store.
    E.g. "Weekly Groceries", "Monthly Household Refill", "Daily Breakfast Staples".
    """
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memo_templates'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='memo_templates'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vendor_memo_templates'
    )
    shopping_mode = models.CharField(
        max_length=20,
        choices=ShoppingMode.choices,
        default=ShoppingMode.REMOTE
    )
    is_favorite = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_favorite', '-created_at']
        unique_together = ('user', 'store', 'name')
        verbose_name = 'Store Memo Template'
        verbose_name_plural = 'Store Memo Templates'

    def save(self, *args, **kwargs):
        if self.store_id and not self.vendor_id:
            if hasattr(self, 'store') and self.store and self.store.vendor:
                self.vendor = self.store.vendor
        super().save(*args, **kwargs)

    @property
    def total_items_count(self) -> int:
        return self.items.count()

    @property
    def estimated_total(self) -> Decimal:
        items = list(self.items.select_related('product').all())
        if not items:
            return Decimal('0.00')
        return sum(item.subtotal for item in items)

    def __str__(self):
        return f"{self.name} ({self.store.name})"


class StoreMemoTemplateItem(BaseModel):
    """An individual line item in a store routine shopping template."""
    template = models.ForeignKey(
        StoreMemoTemplate,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='template_items'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal('1.000')
    )
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['product__aisle', 'product__shelf_location', 'id']
        unique_together = ('template', 'product')
        verbose_name = 'Store Memo Template Item'
        verbose_name_plural = 'Store Memo Template Items'

    @property
    def unit_price(self) -> Decimal:
        if self.product:
            return self.product.effective_price
        return Decimal('0.00')

    @property
    def subtotal(self) -> Decimal:
        return self.quantity * self.unit_price

    def __str__(self):
        return f"{self.product.name} x {self.quantity} in {self.template.name}"
