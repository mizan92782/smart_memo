from decimal import Decimal
from django.db import transaction
from cards.models.card_mod import Card, CardItem
from cards.repositories.card_repository import CardRepository
from products.repositories.product_repository import ProductRepository


class CardService:
    """Encapsulates business operations for Card (Draft Shopping Memo)."""

    @staticmethod
    def get_or_create_active_memo(user, store=None, store_id=None, shopping_mode: str = 'remote', title: str = None) -> Card:
        """Fetch or initialize current draft shopping memo for user and specific store."""
        if store_id and not store:
            from stores.repositories.store_repository import StoreRepository
            store = StoreRepository.get_by_id(store_id)
            if not store:
                raise ValueError("Store not found.")
        return CardRepository.get_or_create_active_card_for_user(
            user=user,
            store=store,
            shopping_mode=shopping_mode,
            title=title
        )

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

    @staticmethod
    def create_saved_memo(
        user,
        store=None,
        store_id=None,
        title: str = "My Saved Memo",
        planned_visit_date=None,
        notes: str = "",
        shopping_mode: str = 'walk_in'
    ) -> Card:
        """Create a dedicated saved memo for a future store visit."""
        if store_id and not store:
            from stores.repositories.store_repository import StoreRepository
            store = StoreRepository.get_by_id(store_id)
            if not store:
                raise ValueError("Store not found.")
        card = Card.objects.create(
            user=user,
            store=store,
            vendor=store.vendor if store else None,
            title=title or "My Saved Memo",
            shopping_mode=shopping_mode,
            notes=notes,
            is_saved_for_later=True,
            planned_visit_date=planned_visit_date,
            is_completed=False
        )
        return card

    @staticmethod
    def save_memo_for_later(card: Card, actor, title: str = None, planned_visit_date=None) -> Card:
        """Move an active shopping memo to saved for later status."""
        if card.is_completed:
            raise ValueError("Cannot save an already completed shopping memo.")
        if card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only modify your own shopping memo.")

        card.is_saved_for_later = True
        update_fields = ['is_saved_for_later', 'updated_at']
        if title:
            card.title = title
            update_fields.append('title')
        if planned_visit_date is not None:
            card.planned_visit_date = planned_visit_date
            update_fields.append('planned_visit_date')
        card.save(update_fields=update_fields)
        return card

    @staticmethod
    @transaction.atomic
    def activate_saved_memo(card: Card, actor, strategy: str = 'swap') -> Card:
        """
        Activate a saved memo into the user's active shopping cart for the store.
        If an existing active memo exists:
          - If empty: automatically replaces it.
          - If non-empty and strategy='swap': safely sets previous active memo to is_saved_for_later=True.
          - If strategy='merge': merges items into existing active memo.
        """
        if card.is_completed:
            raise ValueError("Cannot activate a completed shopping memo.")
        if card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only modify your own shopping memo.")

        if not card.is_saved_for_later:
            return card

        # Check for existing active memo for this store
        existing_active = CardRepository.get_active_card_for_user(user_id=actor.id, store_id=card.store_id)
        if existing_active and existing_active.id != card.id:
            if existing_active.items.count() == 0:
                existing_active.delete()
            elif strategy == 'merge':
                for item in card.items.all():
                    CardRepository.add_item_to_card(
                        card=existing_active,
                        product=item.product,
                        quantity=item.quantity,
                        unit_price=item.unit_price
                    )
                card.items.all().delete()
                card.delete()
                return existing_active
            else:  # swap
                existing_active.is_saved_for_later = True
                existing_active.save(update_fields=['is_saved_for_later', 'updated_at'])

        card.is_saved_for_later = False
        card.save(update_fields=['is_saved_for_later', 'updated_at'])
        return card

    @staticmethod
    @transaction.atomic
    def duplicate_memo(card: Card, actor, new_title: str = None, as_saved: bool = True) -> Card:
        """Duplicate a memo and all its items into a new saved or active memo."""
        if card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only duplicate your own shopping memo.")

        return CardRepository.clone_card_with_items(
            card=card,
            new_title=new_title,
            is_saved_for_later=as_saved
        )

