from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store


class StoreReview(BaseModel):
    """
    Verified Customer Review & Rating for a Store.
    Only customers who completed an order at the store can leave a review.
    Guarantees at most 1 review per completed order.
    """
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='store_reviews'
    )
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='store_review',
        null=True,
        blank=True
    )
    rating = models.PositiveSmallIntegerField()  # 1 to 5
    comment = models.TextField(blank=True, default='')
    is_verified_purchase = models.BooleanField(default=True)
    vendor_reply = models.TextField(blank=True, default='')
    vendor_replied_at = models.DateTimeField(null=True, blank=True)
    is_visible = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Store Review'
        verbose_name_plural = 'Store Reviews'
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name='review_rating_between_1_and_5'
            )
        ]

    def __str__(self):
        return f"{self.customer.email} -> {self.store.name} ({self.rating}★)"
