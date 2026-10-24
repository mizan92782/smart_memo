from django.db import models
from django.conf import settings
from django.utils.text import slugify
from shared.base.base_model import BaseModel


class Store(BaseModel):
    """
    Store model representing a vendor's physical/online store.
    Serves as the multi-tenant boundary for categories, products, inventory, and orders.
    """
    vendor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stores'
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True, default="")
    phone_number = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    address = models.TextField(blank=True, default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=True, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_notes = models.CharField(max_length=255, blank=True, default="")
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    delivery_enabled = models.BooleanField(default=True)
    pickup_enabled = models.BooleanField(default=True)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, db_index=True)
    total_reviews = models.IntegerField(default=0)

    class Meta:
        ordering = ['name']
        verbose_name = 'Store'
        verbose_name_plural = 'Stores'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            candidate = base_slug
            counter = 1
            while Store.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base_slug}-{counter}"
                counter += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.vendor.email})"
