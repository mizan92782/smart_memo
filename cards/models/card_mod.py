from django.db import models
from django.conf import settings
from shared.base.base_model import BaseModel
from products.models.product_mod import Product


from stores.models.store_mod import Store


class Card(BaseModel):
    """Card (Cart / Memo Card) model to group items for a user or session."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cards'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cards'
    )
    title = models.CharField(max_length=200, default="My Memo Card")
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Card'
        verbose_name_plural = 'Cards'

    def __str__(self):
        return f"{self.title} (#{self.id})"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())


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

    class Meta:
        verbose_name = 'Card Item'
        verbose_name_plural = 'Card Items'

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product.effective_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity} in {self.card.title}"
