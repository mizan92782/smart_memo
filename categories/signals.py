"""
categories/signals.py — Django Signals for Categories
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from categories.models.category_mod import Category
from infra.redis.client import category_cache


@receiver(post_save, sender=Category)
def category_post_save_handler(sender, instance, created, **kwargs):
    """Invalidate category cache on create/update."""
    category_cache.delete(f"category:{instance.id}")
    category_cache.delete("categories:all")


@receiver(post_delete, sender=Category)
def category_post_delete_handler(sender, instance, **kwargs):
    """Invalidate category cache on delete."""
    category_cache.delete(f"category:{instance.id}")
    category_cache.delete("categories:all")
