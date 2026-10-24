from decimal import Decimal
from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from products.models.product_mod import Product


from stores.models.store_mod import Store


class ShoppingMode(models.TextChoices):
    REMOTE = 'remote', 'Remote / Home Order'
    WALK_IN = 'walk_in', 'In-Store Walk-In'


class Card(BaseModel):
    """Card (Cart / Memo Card) model to group items for a user or session."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cards'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vendor_cards'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cards'
    )
    coupon = models.ForeignKey(
        'stores.Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cards'
    )
    title = models.CharField(max_length=200, default="My Memo Card")
    shopping_mode = models.CharField(
        max_length=20,
        choices=ShoppingMode.choices,
        default=ShoppingMode.REMOTE
    )
    notes = models.TextField(blank=True, default='')
    is_completed = models.BooleanField(default=False)
    is_saved_for_later = models.BooleanField(default=False)
    planned_visit_date = models.DateField(null=True, blank=True)
    budget_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    loyalty_points_redeemed = models.PositiveIntegerField(default=0)
    loyalty_stamps_redeemed = models.PositiveIntegerField(default=0)
    loyalty_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Card'
        verbose_name_plural = 'Cards'

    @property
    def customer(self):
        return self.user

    @customer.setter
    def customer(self, value):
        self.user = value

    def save(self, *args, **kwargs):
        if self.store_id:
            if hasattr(self, 'store') and self.store and self.store.vendor:
                self.vendor = self.store.vendor
        else:
            self.vendor = None

        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
            if 'vendor' not in update_fields:
                update_fields.add('vendor')
            kwargs['update_fields'] = update_fields

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} (#{self.id})"

    @property
    def total_price(self):
        items = list(self.items.all())
        if not items:
            return Decimal('0.00')
        return sum(item.subtotal for item in items)

    @property
    def discount_amount(self):
        if not self.coupon or not self.store:
            return Decimal('0.00')
        if self.coupon.store_id != self.store_id:
            return Decimal('0.00')
        is_valid, _ = self.coupon.is_valid_for(self.user, self.total_price)
        if not is_valid:
            return Decimal('0.00')
        return self.coupon.calculate_discount(self.total_price)

    @property
    def estimated_total(self):
        return max(Decimal('0.00'), self.total_price - self.discount_amount - self.loyalty_discount_amount)

    @property
    def total_items_count(self) -> int:
        return self.items.count()

    @property
    def picked_items_count(self) -> int:
        return self.items.filter(is_picked=True).count()

    @property
    def is_fully_picked(self) -> bool:
        total = self.total_items_count
        return total > 0 and self.picked_items_count == total

    @property
    def picking_progress_percent(self) -> float:
        total = self.total_items_count
        if total == 0:
            return 0.0
        return round((self.picked_items_count / total) * 100.0, 1)

    @property
    def budget_remaining(self):
        if self.budget_limit is None:
            return None
        return self.budget_limit - self.estimated_total

    @property
    def is_over_budget(self) -> bool:
        if self.budget_limit is None:
            return False
        return self.estimated_total > self.budget_limit

    @property
    def budget_used_percent(self):
        if not self.budget_limit or self.budget_limit <= Decimal('0.00'):
            return None
        return round(float((self.estimated_total / self.budget_limit) * Decimal('100.0')), 1)


class CardItem(BaseModel):
    """An individual product entry in a Card."""
    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='card_items'
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_picked = models.BooleanField(default=False, db_index=True)
    picked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Card Item'
        verbose_name_plural = 'Card Items'

    @property
    def subtotal(self):
        return (Decimal(str(self.quantity)) * Decimal(str(self.unit_price))).quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.effective_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} in {self.card.title}"
