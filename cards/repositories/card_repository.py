"""
cards/repositories/card_repository.py — Database Query Logic for Card

Senior Pattern: Repositories are NOT instantiated (static methods only).
Single source of truth for Card DB interactions.
"""
from decimal import Decimal
from typing import Optional
from django.db.models import QuerySet
from cards.models.card_mod import Card, CardItem


class CardRepository:
    """Handles all database operations for the Card model."""

    @staticmethod
    def get_by_id(card_id: int) -> Optional[Card]:
        """Fetch card by primary key with items prefetched."""
        return Card.objects.select_related('store', 'user').prefetch_related('items__product').filter(pk=card_id).first()

    @staticmethod
    def get_by_user(user_id: int) -> QuerySet[Card]:
        """Fetch cards for a given user."""
        return Card.objects.select_related('store').prefetch_related('items__product').filter(user_id=user_id)

    @staticmethod
    def get_active_card_for_user(user_id: int) -> Optional[Card]:
        """Fetch current active (uncompleted) card for user."""
        return Card.objects.select_related('store').prefetch_related('items__product').filter(user_id=user_id, is_completed=False).first()

    @staticmethod
    def get_or_create_active_card_for_user(user) -> Card:
        """Fetch or create current active (uncompleted) draft card for user."""
        card = Card.objects.select_related('store').prefetch_related('items__product').filter(user=user, is_completed=False).first()
        if not card:
            card = Card.objects.create(user=user, title="My Memo Card")
        return card

    @staticmethod
    def create_card(user=None, user_id: Optional[int] = None, store=None, title: str = "My Memo Card") -> Card:
        """Create a new card."""
        uid = user.id if user else user_id
        return Card.objects.create(user_id=uid, store=store, title=title)

    @staticmethod
    def add_item_to_card(card: Card, product, quantity: Decimal, unit_price: Optional[Decimal] = None) -> CardItem:
        """Add an item or increment quantity if already present."""
        price = unit_price or product.effective_price
        item, created = CardItem.objects.get_or_create(
            card=card,
            product=product,
            defaults={
                'quantity': quantity,
                'unit_price': price
            }
        )
        if not created:
            item.quantity = Decimal(str(item.quantity)) + Decimal(str(quantity))
            item.unit_price = price
            item.save(update_fields=['quantity', 'unit_price', 'updated_at'])
        return item

    @staticmethod
    def update_item_quantity(item: CardItem, quantity: Decimal) -> CardItem:
        """Update an item's quantity and refresh with current effective price."""
        item.quantity = Decimal(str(quantity))
        item.unit_price = item.product.effective_price
        item.save(update_fields=['quantity', 'unit_price', 'updated_at'])
        return item

    @staticmethod
    def remove_item(card_item_id: int) -> None:
        """Remove an item from a card."""
        CardItem.objects.filter(pk=card_item_id).delete()

    @staticmethod
    def remove_item_from_card(card: Card, item: CardItem) -> None:
        """Remove an item from a card and reset store and coupon if memo becomes empty."""
        item.delete()
        if card.items.count() == 0:
            card.store = None
            card.coupon = None
            card.save(update_fields=['store', 'coupon', 'updated_at'])

    @staticmethod
    def clear_card(card: Card) -> None:
        """Remove all items from draft memo and reset store and coupon binding."""
        card.items.all().delete()
        card.store = None
        card.coupon = None
        card.save(update_fields=['store', 'coupon', 'updated_at'])
