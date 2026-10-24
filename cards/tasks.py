"""
cards/tasks.py — Background Tasks (Celery) for Cards
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from cards.models.card_mod import Card

logger = logging.getLogger(__name__)


@shared_task
def clean_abandoned_cards_task():
    """Background task to remove abandoned cards older than 30 days."""
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count, _ = Card.objects.filter(is_completed=False, updated_at__lt=cutoff_date).delete()
    logger.info("Cleaned up %d abandoned cards", deleted_count)
    return deleted_count
