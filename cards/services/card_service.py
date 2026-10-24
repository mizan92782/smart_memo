from decimal import Decimal
from django.db import transaction
from cards.models.card_mod import Card, CardItem
from cards.repositories.card_repository import CardRepository
from products.repositories.product_repository import ProductRepository


class CardService:
    """Encapsulates business operations for Card (Draft Shopping Memo)."""

    @staticmethod
    def add_product_to_card(card_id: int, product_id: int, quantity: Decimal = Decimal('1')) -> CardItem:
        """Add product to card enforcing single-store rule and availability."""
        card = CardRepository.get_by_id(card_id)
        if not card:
            raise ValueError("Card not found.")

        product = ProductRepository.get_by_id(product_id)
        if not product:
            raise ValueError("Product not found.")

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
    def checkout_card(
        card: Card,
        customer,
        fulfillment_type: str = 'pickup',
        delivery_address: str = "",
        idempotency_key: str = None,
        notes: str = ""
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
            notes=notes
        )

