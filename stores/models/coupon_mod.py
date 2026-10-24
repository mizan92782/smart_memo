from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store


class DiscountType(models.TextChoices):
    PERCENTAGE = 'percentage', 'Percentage Discount'
    FIXED = 'fixed', 'Fixed Amount Discount'


class Coupon(BaseModel):
    """Store-scoped promotional discount coupon."""
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='coupons'
    )
    code = models.CharField(max_length=32)
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    min_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    max_uses_per_customer = models.PositiveIntegerField(default=1)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('store', 'code')
        indexes = [
            models.Index(fields=['store', 'code', 'is_active']),
        ]

    def __str__(self):
        return f"{self.code} ({self.store.name})"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def is_valid_for(self, customer, subtotal: Decimal, now=None):
        """Validate coupon applicability for a customer and order subtotal."""
        if not self.is_active:
            return False, "This coupon is currently inactive."

        if now is None:
            now = timezone.now()

        if self.start_date and now < self.start_date:
            return False, f"This coupon is not active until {self.start_date.strftime('%Y-%m-%d')}."

        if self.end_date and now > self.end_date:
            return False, "This coupon has expired."

        if subtotal < self.min_order_amount:
            return False, f"Minimum order amount of {self.min_order_amount} required to use this coupon."

        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False, "This coupon has reached its maximum total uses."

        if customer and customer.is_authenticated:
            customer_uses = self.usages.filter(customer=customer).count()
            if customer_uses >= self.max_uses_per_customer:
                return False, f"You have already used this coupon the maximum allowed times ({self.max_uses_per_customer})."

        return True, ""

    def calculate_discount(self, subtotal: Decimal) -> Decimal:
        """Calculate authoritative discount amount for a given order subtotal."""
        if subtotal <= Decimal('0.00'):
            return Decimal('0.00')

        if self.discount_type == DiscountType.PERCENTAGE:
            discount = (subtotal * self.discount_value / Decimal('100.00')).quantize(Decimal('0.01'))
            if self.max_discount_amount is not None:
                discount = min(discount, self.max_discount_amount)
        else:
            discount = min(self.discount_value, subtotal)

        return min(discount, subtotal)


class CouponUsage(BaseModel):
    """Historical ledger entry for each coupon redemption against an order."""
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        related_name='usages'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='coupon_usages'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='coupon_usages'
    )
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['coupon', 'customer']),
        ]

    def __str__(self):
        return f"{self.customer.email} used {self.coupon.code} on Order #{self.order.id}"
