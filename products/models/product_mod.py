from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import ArrayField

from shared.enums.unit_enums import MeasurementUnit
from shared.enums.currency_unit import CurrencyUnit
from shared.utilities.product_images_path import ProductImagePath
from shared.utilities.products_default_description import product_default_description
from categories.models.category_mod import Category
from stores.models.store_mod import Store
from shared.base.base_model import BaseModel


class Product(BaseModel):
    """Product model representing an item for sale in a store."""

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=200)
    second_name = models.CharField(max_length=200, default="")
    sku = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(default=product_default_description)
    tags = ArrayField(
        models.CharField(max_length=50),
        size=10,
        blank=True,
        default=list
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )

    measure = models.SmallIntegerField(blank=False, null=False, default=1)
    unit = models.CharField(
        max_length=10,
        choices=MeasurementUnit.choices,
        default=MeasurementUnit.KILOGRAM
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)

    currency = models.CharField(
        max_length=10,
        choices=CurrencyUnit.choices,
        default=CurrencyUnit.BDT
    )
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=5)
    is_active = models.BooleanField(default=True)

    offer = models.BooleanField(default=False)
    offered_discount = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    offered_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    offer_start_date = models.DateTimeField(null=True, blank=True)
    offer_end_date = models.DateTimeField(null=True, blank=True)

    offered_count = models.SmallIntegerField(default=0)
    offered_count_unit = models.CharField(
        max_length=10,
        choices=MeasurementUnit.choices,
        blank=True,
        null=True
    )

    image = models.ImageField(upload_to=ProductImagePath, blank=True, null=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def is_in_stock(self) -> bool:
        return self.stock > 0

    def is_offer_active(self, now=None) -> bool:
        """Determines if the product offer is currently valid and active."""
        if not self.offer:
            return False
        if now is None:
            from django.utils import timezone
            now = timezone.now()
        if self.offer_start_date and now < self.offer_start_date:
            return False
        if self.offer_end_date and now > self.offer_end_date:
            return False
        return True

    @property
    def effective_price(self) -> Decimal:
        """Authoritative current selling price considering offer active window."""
        if self.is_offer_active():
            return self.offered_price
        return self.price

    def save(self, *args, **kwargs):
        self.name = self.name.title()

        if self.tags is None:
            self.tags = []
        if self.name not in self.tags:
            self.tags.append(self.name)
        if self.second_name and self.second_name not in self.tags:
            self.tags.append(self.second_name)
        if hasattr(self, 'category') and self.category and hasattr(self.category, 'name') and self.category.name not in self.tags:
            self.tags.append(self.category.name)

        if self.price is not None and self.offered_discount is not None:
            disc_dec = Decimal(str(self.offered_discount))
            price_dec = Decimal(str(self.price))
            self.offered_price = (price_dec - (price_dec * (disc_dec / Decimal('100')))).quantize(Decimal('0.01'))

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} - {self.category}'
