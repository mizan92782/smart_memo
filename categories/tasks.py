"""
categories/tasks.py — Background Tasks (Celery) for Categories
"""
import logging
from celery import shared_task
from categories.models.category_mod import Category
from infra.redis.client import category_cache

logger = logging.getLogger(__name__)


@shared_task
def sync_categories_cache_task():
    """Background task to preload categories in Redis cache."""
    categories = list(Category.objects.values('id', 'name'))
    category_cache.set("categories:all", categories, ttl=3600)
    logger.info("Successfully preloaded %d categories in cache", len(categories))
    return len(categories)
