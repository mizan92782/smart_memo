from django.db import models
from django.urls import reverse
from stores.models.store_mod import Store
from shared.base.base_model import BaseModel


class Category(BaseModel):
    """Category model representing a product category scoped to a store."""
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='categories',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'
        constraints = [
            models.UniqueConstraint(
                fields=['store', 'name'],
                name='unique_store_category'
            )
        ]

    def save(self, *args, **kwargs):
        self.name = self.name.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.store.name})" if self.store else self.name

    def get_category_products_url(self):
        """Return the reverse URL for products under this category."""
        return reverse('category_products', kwargs={'pk': self.pk})
