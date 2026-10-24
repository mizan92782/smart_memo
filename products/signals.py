"""
products/signals.py — Django Signals for Products
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from products.models.product_mod import Product
from infra.redis.client import product_cache


@receiver(post_save, sender=Product)
def product_post_save_handler(sender, instance, created, **kwargs):
    """Invalidate or update product cache on save."""
    product_cache.delete(f"product:{instance.id}")
    product_cache.delete("products:all")


@receiver(post_delete, sender=Product)
def product_post_delete_handler(sender, instance, **kwargs):
    """Invalidate product cache on delete."""
    product_cache.delete(f"product:{instance.id}")
    product_cache.delete("products:all")
