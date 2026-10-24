"""
products/tasks.py — Background Tasks (Celery) for Products
"""
import logging
from celery import shared_task
from django.utils import timezone
from products.models.product_mod import Product

logger = logging.getLogger(__name__)


@shared_task
def expire_product_offers_task():
    """Periodic task to deactivate expired promotional offers."""
    now = timezone.now()
    expired_count = Product.objects.filter(
        offer=True,
        offer_end_date__lt=now
    ).update(offer=False)
    logger.info("Expired %d product offers at %s", expired_count, now)
    return expired_count
