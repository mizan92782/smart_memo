from decimal import Decimal
from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store


class LoyaltyProgramType(models.TextChoices):
    POINTS = 'points', 'Points Based'
    STAMPS = 'stamps', 'Visit Stamps Punch Card'


class StoreLoyaltyProgram(BaseModel):
    """Store-scoped customer loyalty configuration managed by the store vendor."""
    store = models.OneToOneField(
        Store,
        on_delete=models.CASCADE,
        related_name='loyalty_program'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vendor_loyalty_programs'
    )
    is_active = models.BooleanField(default=False)
    program_type = models.CharField(
        max_length=20,
        choices=LoyaltyProgramType.choices,
        default=LoyaltyProgramType.POINTS
    )
    # Points Configuration: e.g. earn 1 point per $1 spent
    points_per_currency_unit = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00')
    )
    # 1 point = $0.05 discount (so 100 points = $5.00)
    currency_per_point_redemption = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0500')
    )
    min_points_to_redeem = models.PositiveIntegerField(default=50)

    # Stamp / Punch Card Configuration: e.g. 10 visits/orders = $5.00 discount
    stamps_for_reward = models.PositiveIntegerField(default=10)
    stamp_reward_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('5.00')
    )
    min_order_for_stamp = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('10.00')
    )

    class Meta:
        verbose_name = 'Store Loyalty Program'
        verbose_name_plural = 'Store Loyalty Programs'

    def save(self, *args, **kwargs):
        if self.store_id and not self.vendor_id:
            if hasattr(self, 'store') and self.store and self.store.vendor:
                self.vendor = self.store.vendor
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Loyalty Program for {self.store.name} ({self.program_type})"


class CustomerStoreLoyalty(BaseModel):
    """Customer loyalty card and punch card account scoped strictly to a specific store."""
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='store_loyalties'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='customer_loyalties'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vendor_customer_loyalties'
    )
    points_balance = models.PositiveIntegerField(default=0)
    stamps_balance = models.PositiveIntegerField(default=0)
    total_points_earned = models.PositiveIntegerField(default=0)
    total_stamps_earned = models.PositiveIntegerField(default=0)
    total_rewards_redeemed = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('customer', 'store')
        ordering = ['-points_balance', '-stamps_balance']
        verbose_name = 'Customer Store Loyalty'
        verbose_name_plural = 'Customer Store Loyalties'

    def save(self, *args, **kwargs):
        if self.store_id and not self.vendor_id:
            if hasattr(self, 'store') and self.store and self.store.vendor:
                self.vendor = self.store.vendor
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer.email} @ {self.store.name} (Pts: {self.points_balance}, Stamps: {self.stamps_balance})"


class LoyaltyTransactionType(models.TextChoices):
    EARNED_PURCHASE = 'earned_purchase', 'Earned from Completed Order'
    REDEEMED_MEMO = 'redeemed_memo', 'Redeemed on Shopping Memo'
    REFUND_CANCELLED = 'refund_cancelled', 'Refunded from Cancelled Order'
    MANUAL_ADJUSTMENT = 'manual_adjustment', 'Manual Vendor Adjustment'


class LoyaltyTransaction(BaseModel):
    """Append-only audit ledger entry for store loyalty point and visit stamp mutations."""
    loyalty_account = models.ForeignKey(
        CustomerStoreLoyalty,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loyalty_transactions'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='store_loyalty_transactions'
    )
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='vendor_loyalty_transactions'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loyalty_transactions'
    )
    sales_memo = models.ForeignKey(
        'orders.SalesMemo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='loyalty_transactions'
    )
    transaction_type = models.CharField(
        max_length=30,
        choices=LoyaltyTransactionType.choices
    )
    points_change = models.IntegerField(default=0)
    stamps_change = models.IntegerField(default=0)
    points_balance_after = models.PositiveIntegerField()
    stamps_balance_after = models.PositiveIntegerField()
    discount_amount_applied = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    notes = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Loyalty Transaction'
        verbose_name_plural = 'Loyalty Transactions'

    def save(self, *args, **kwargs):
        if self.store_id and not self.vendor_id:
            if hasattr(self, 'store') and self.store and self.store.vendor:
                self.vendor = self.store.vendor
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type} ({self.customer.email} @ {self.store.name})"
