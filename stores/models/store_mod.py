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
    secondary_phone = models.CharField(max_length=30, blank=True, default="")
    whatsapp_number = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    owner_name = models.CharField(max_length=150, blank=True, default="")
    logo_url = models.URLField(max_length=500, blank=True, default="")
    cover_photo_url = models.URLField(max_length=500, blank=True, default="")
    website_url = models.URLField(max_length=255, blank=True, default="")
    social_links = models.JSONField(default=dict, blank=True)
    shop_type = models.CharField(
        max_length=30,
        choices=[
            ('hybrid', 'Physical Store + Online Delivery'),
            ('physical_only', 'Physical Walk-In Only'),
            ('online_only', 'Online Delivery Only')
        ],
        default='hybrid'
    )
    public_url_slug = models.CharField(max_length=200, blank=True, default="", db_index=True)
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

        if not self.public_url_slug:
            clean_slug = self.slug.lower()
            self.public_url_slug = f"{clean_slug}.com" if not clean_slug.endswith('.com') else clean_slug

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.vendor.email})"
