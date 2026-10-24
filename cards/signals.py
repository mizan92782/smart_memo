"""
cards/signals.py — Django Signals for Cards
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from cards.models.card_mod import CardItem


@receiver(post_save, sender=CardItem)
def card_item_saved_handler(sender, instance, created, **kwargs):
    """Triggered when card items are updated."""
    pass
