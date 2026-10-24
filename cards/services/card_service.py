from decimal import Decimal
from django.db import transaction
from cards.models.card_mod import Card, CardItem
from cards.repositories.card_repository import CardRepository
from products.repositories.product_repository import ProductRepository


class CardService:
    """Encapsulates business operations for Card (Draft Shopping Memo)."""

    @staticmethod
    def get_or_create_active_memo(user) -> Card:
        """Fetch or initialize current draft shopping memo for user."""
        return CardRepository.get_or_create_active_card_for_user(user)

    @staticmethod
    def add_product_to_card(card_id: int, product_id: int, quantity: Decimal = Decimal('1'), actor=None) -> CardItem:
        """Add product to card enforcing single-store rule, availability, and memo ownership."""
        card = CardRepository.get_by_id(card_id)
        if not card:
            raise ValueError("Card not found.")

        if card.is_completed:
            raise ValueError("Cannot modify an already completed shopping memo.")

        if actor and card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only modify your own shopping memo.")

        product = ProductRepository.get_by_id(product_id)
        if not product or product.is_deleted or not product.is_active:
            raise ValueError("Product not found or inactive.")

        if card.store is None and product.store is not None:
            card.store = product.store
            card.save(update_fields=['store', 'updated_at'])
        elif card.store is not None and product.store is not None and card.store != product.store:
            raise ValueError("All items in a shopping memo must belong to the same store.")

        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Quantity must be strictly positive.")

        return CardRepository.add_item_to_card(card=card, product=product, quantity=qty)

    @staticmethod
    def update_item_quantity(card_id: int, item_id: int, quantity: Decimal, actor) -> CardItem:
        """Update the quantity of an item within the draft shopping memo."""
        card = CardRepository.get_by_id(card_id)
        if not card:
            raise ValueError("Card not found.")

        if card.is_completed:
            raise ValueError("Cannot modify an already completed shopping memo.")

        if card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only modify your own shopping memo.")

        item = card.items.filter(pk=item_id).first()
        if not item:
            raise ValueError("Item not found in shopping memo.")

        qty = Decimal(str(quantity))
        if qty <= 0:
            raise ValueError("Quantity must be strictly positive.")

        return CardRepository.update_item_quantity(item=item, quantity=qty)

    @staticmethod
    def remove_item_from_card(card_id: int, item_id: int, actor) -> None:
        """Remove an item from draft memo. If memo becomes empty, resets store."""
        card = CardRepository.get_by_id(card_id)
        if not card:
            raise ValueError("Card not found.")

        if card.is_completed:
            raise ValueError("Cannot modify an already completed shopping memo.")

        if card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only modify your own shopping memo.")

        item = card.items.filter(pk=item_id).first()
        if not item:
            raise ValueError("Item not found in shopping memo.")

        CardRepository.remove_item_from_card(card=card, item=item)

    @staticmethod
    def clear_card(card_id: int, actor) -> None:
        """Clear all items from draft shopping memo and reset store binding."""
        card = CardRepository.get_by_id(card_id)
        if not card:
            raise ValueError("Card not found.")

        if card.is_completed:
            raise ValueError("Cannot modify an already completed shopping memo.")

        if card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only modify your own shopping memo.")

        CardRepository.clear_card(card=card)

    @staticmethod
    def checkout_card(
        card: Card,
        customer,
        fulfillment_type: str = 'pickup',
        delivery_address: str = "",
        idempotency_key: str = None,
        notes: str = "",
        address_id: int = None
    ):
        """
        Transition draft card to submitted order.
        Atomically reserves stock and creates snapshot records.
        """
        if card.is_completed:
            raise ValueError("This shopping memo has already been checked out.")

        from orders.services.order_service import OrderService
        return OrderService.submit_order_from_card(
            card=card,
            customer=customer,
            fulfillment_type=fulfillment_type,
            delivery_address=delivery_address,
            idempotency_key=idempotency_key,
            notes=notes,
            address_id=address_id
        )

