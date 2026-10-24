"""
cards/repositories/card_repository.py — Database Query Logic for Card

Senior Pattern: Repositories are NOT instantiated (static methods only).
Single source of truth for Card DB interactions.
"""
from typing import Optional
from django.db.models import QuerySet
from cards.models.card_mod import Card, CardItem


class CardRepository:
    """Handles all database operations for the Card model."""

    @staticmethod
    def get_by_id(card_id: int) -> Optional[Card]:
        """Fetch card by primary key with items prefetched."""
        return Card.objects.prefetch_related('items__product').filter(pk=card_id).first()

    @staticmethod
    def get_by_user(user_id: int) -> QuerySet[Card]:
        """Fetch cards for a given user."""
        return Card.objects.prefetch_related('items__product').filter(user_id=user_id)

    @staticmethod
    def get_active_card_for_user(user_id: int) -> Optional[Card]:
        """Fetch current active (uncompleted) card for user."""
        return Card.objects.filter(user_id=user_id, is_completed=False).first()

    @staticmethod
    def create_card(user=None, user_id: Optional[int] = None, store=None, title: str = "My Memo Card") -> Card:
        """Create a new card."""
        uid = user.id if user else user_id
        return Card.objects.create(user_id=uid, store=store, title=title)

    @staticmethod
    def add_item_to_card(card: Card, product, quantity: float, unit_price: float = None) -> CardItem:
        """Add an item or increment quantity if already present."""
        item, created = CardItem.objects.get_or_create(
            card=card,
            product=product,
            defaults={
                'quantity': quantity,
                'unit_price': unit_price or (product.offered_price if product.offer else product.price)
            }
        )
        if not created:
            item.quantity += quantity
            item.save()
        return item

    @staticmethod
    def remove_item(card_item_id: int) -> None:
        """Remove an item from a card."""
        CardItem.objects.filter(pk=card_item_id).delete()
