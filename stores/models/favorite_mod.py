from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from stores.models.store_mod import Store


class FavoriteStore(BaseModel):
    """
    Customer's saved/favorite store.
    Enforces a unique customer-store relationship for idempotency.
    """
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorite_stores'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Favorite Store'
        verbose_name_plural = 'Favorite Stores'
        constraints = [
            models.UniqueConstraint(
                fields=['customer', 'store'],
                name='unique_customer_store_favorite'
            )
        ]

    def __str__(self):
        return f"{self.customer.email} -> {self.store.name}"
