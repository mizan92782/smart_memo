from django.db import models
from shared.base.base_model import BaseModel
from shared.utilities.product_images_path import ProductImagePath
from .product_mod import Product


class ProductImage(BaseModel):
    """
    ProductImage model representing gallery photos for a product.
    Supports multiple photos per product, primary thumbnail selection, and display ordering.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to=ProductImagePath, blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, default="")
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)
    alt_text = models.CharField(max_length=150, blank=True, default="")

    class Meta:
        ordering = ['display_order', '-is_primary', '-created_at']
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    @property
    def effective_url(self) -> str:
        if self.image:
            try:
                return self.image.url
            except Exception:
                pass
        return self.image_url or ""

    def __str__(self):
        return f"Image for {self.product.name} (Primary: {self.is_primary})"
