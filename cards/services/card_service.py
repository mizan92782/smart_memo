from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from cards.models.card_mod import Card, CardItem
from cards.repositories.card_repository import CardRepository
from products.models.product_mod import Product
from stores.models.store_mod import Store
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
    def scan_add_product(card_id: int, code: str, quantity: Decimal = Decimal('1'), actor=None) -> CardItem:
        """
        In-store shelf scanning: lookup product by barcode or SKU and add to draft memo.
        Enforces store scoping: if card is bound to a store, only products of that store are matched.
        """
        card = CardRepository.get_by_id(card_id)
        if not card:
            raise ValueError("Card not found.")

        if not card.store_id:
            raise ValueError("Draft shopping memo must be bound to a store to scan in-store shelf barcodes.")

        if not code or not str(code).strip():
            raise ValueError("Barcode or SKU code is required.")

        product = ProductRepository.get_by_barcode_or_sku(card.store_id, str(code).strip())
        if not product:
            raise ValueError(f"No product with barcode or SKU '{code}' found in {card.store.name}.")

        return CardService.add_product_to_card(
            card_id=card.id,
            product_id=product.id,
            quantity=quantity,
            actor=actor
        )

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

    @staticmethod
    def toggle_item_picked(card: Card, item_id: int, is_picked: bool = None, actor=None) -> CardItem:
        """Toggle or set physical in-store picked status of a line item."""
        if card.is_completed:
            raise ValueError("Cannot modify items in a completed shopping memo.")
        if actor and card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only modify items in your own shopping memo.")

        item = card.items.filter(id=item_id).first()
        if not item:
            raise ValueError("Item not found in this shopping memo.")

        if is_picked is None:
            item.is_picked = not item.is_picked
        else:
            item.is_picked = bool(is_picked)

        item.picked_at = timezone.now() if item.is_picked else None
        item.save(update_fields=['is_picked', 'picked_at', 'updated_at'])
        return item

    @staticmethod
    @transaction.atomic
    def batch_pick_items(card: Card, item_ids: list, is_picked: bool = True, actor=None) -> Card:
        """Batch update picked status for multiple items in a shopping memo."""
        if card.is_completed:
            raise ValueError("Cannot modify items in a completed shopping memo.")
        if actor and card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only modify items in your own shopping memo.")

        now = timezone.now() if is_picked else None
        card.items.filter(id__in=item_ids).update(
            is_picked=bool(is_picked),
            picked_at=now,
            updated_at=timezone.now()
        )
        return card

    @staticmethod
    def get_card_items_sorted(card: Card, sort_by: str = None):
        """Retrieve card items, optionally ordered by physical store aisle layout."""
        qs = card.items.select_related('product', 'product__category', 'product__store')
        if sort_by == 'aisle':
            return qs.order_by('product__aisle', 'product__shelf_location', 'id')
        return qs.order_by('id')

    @staticmethod
    def set_budget_limit(card: Card, budget_limit, actor=None) -> Card:
        """Set or update the spending ceiling/budget limit for a shopping memo."""
        if card.is_completed:
            raise ValueError("Cannot set budget on a completed shopping memo.")
        if actor and card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only modify your own shopping memo.")

        if budget_limit is not None and str(budget_limit).strip() != "":
            try:
                dec_limit = Decimal(str(budget_limit))
                if dec_limit < Decimal('0.00'):
                    raise ValueError("Budget limit must be greater than or equal to 0.")
                card.budget_limit = dec_limit
            except Exception as e:
                if isinstance(e, ValueError):
                    raise
                raise ValueError("Invalid budget limit amount.")
        else:
            card.budget_limit = None

        card.save(update_fields=['budget_limit', 'updated_at'])
        return card

    @staticmethod
    def compare_with_store(card: Card, target_store_id: int, actor=None) -> dict:
        """
        Compare products, pricing, and stock availability between the current memo's store
        and a target vendor store.
        """
        if actor and card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only compare your own shopping memo.")

        target_store = Store.objects.filter(id=target_store_id, is_deleted=False).first()
        if not target_store:
            raise ValueError("Target store not found.")
        if not target_store.is_active:
            raise ValueError("Target store is not currently active.")
        if card.store_id == target_store.id:
            raise ValueError("Target store must be different from current store.")

        matched_items = []
        missing_items = []
        source_matched_total = Decimal('0.00')
        target_matched_total = Decimal('0.00')

        source_items = list(card.items.select_related('product', 'product__store'))

        for item in source_items:
            source_prod = item.product
            # Look up product in target store by barcode, then SKU, then Name
            target_prod = None
            if source_prod.barcode:
                target_prod = Product.objects.filter(
                    store=target_store,
                    barcode=source_prod.barcode,
                    is_deleted=False,
                    is_active=True
                ).first()

            if not target_prod and source_prod.sku:
                target_prod = Product.objects.filter(
                    store=target_store,
                    sku=source_prod.sku,
                    is_deleted=False,
                    is_active=True
                ).first()

            if not target_prod:
                target_prod = Product.objects.filter(
                    store=target_store,
                    name__iexact=source_prod.name,
                    is_deleted=False,
                    is_active=True
                ).first()

            if target_prod:
                source_line_total = item.subtotal
                target_unit_price = target_prod.effective_price
                target_line_total = (item.quantity * target_unit_price).quantize(Decimal('0.01'))
                has_stock = (target_prod.stock >= item.quantity)
                line_diff = (target_line_total - source_line_total).quantize(Decimal('0.01'))

                matched_items.append({
                    'source_item_id': item.id,
                    'source_product_id': source_prod.id,
                    'target_product_id': target_prod.id,
                    'product_name': source_prod.name,
                    'barcode': source_prod.barcode,
                    'sku': source_prod.sku,
                    'quantity': str(item.quantity),
                    'source_unit_price': str(item.unit_price),
                    'source_line_total': str(source_line_total),
                    'target_unit_price': str(target_unit_price),
                    'target_line_total': str(target_line_total),
                    'price_difference': str(line_diff),
                    'has_stock': has_stock,
                    'available_stock': str(target_prod.stock),
                    'target_product': target_prod
                })
                source_matched_total += source_line_total
                target_matched_total += target_line_total
            else:
                missing_items.append({
                    'source_item_id': item.id,
                    'source_product_id': source_prod.id,
                    'product_name': source_prod.name,
                    'barcode': source_prod.barcode,
                    'sku': source_prod.sku,
                    'quantity': str(item.quantity),
                    'source_unit_price': str(item.unit_price),
                    'source_line_total': str(item.subtotal),
                    'reason': 'Not carried by target store'
                })

        savings = (source_matched_total - target_matched_total).quantize(Decimal('0.01'))
        can_fully_fulfill = (len(missing_items) == 0 and all(m['has_stock'] for m in matched_items))

        # Filter out model instance from dict before serialization
        clean_matched = []
        for m in matched_items:
            entry = dict(m)
            entry.pop('target_product', None)
            clean_matched.append(entry)

        return {
            'source_store': {
                'id': card.store.id if card.store else None,
                'name': card.store.name if card.store else "Unassigned",
            },
            'target_store': {
                'id': target_store.id,
                'name': target_store.name,
            },
            'total_items_in_memo': len(source_items),
            'matched_items_count': len(matched_items),
            'missing_items_count': len(missing_items),
            'source_matched_total': str(source_matched_total),
            'target_matched_total': str(target_matched_total),
            'savings_at_target': str(savings),
            'is_target_cheaper': savings > Decimal('0.00'),
            'can_fully_fulfill': can_fully_fulfill,
            'matched_items': clean_matched,
            'missing_items': missing_items,
            '_internal_matched_items': matched_items
        }

    @staticmethod
    @transaction.atomic
    def transfer_to_store(card: Card, target_store_id: int, actor=None, clone: bool = False, omit_missing: bool = True) -> Card:
        """
        Transfer or clone a shopping memo to another vendor's store, re-binding items to the
        target store's catalog products and local prices.
        """
        if card.is_completed:
            raise ValueError("Cannot transfer a completed shopping memo.")
        if actor and card.user and card.user != actor and not getattr(actor, 'is_superuser', False):
            raise PermissionError("You can only transfer your own shopping memo.")

        target_store = Store.objects.filter(id=target_store_id, is_deleted=False).first()
        if not target_store:
            raise ValueError("Target store not found.")
        if not target_store.is_active:
            raise ValueError("Target store is not currently active.")
        if card.store_id == target_store.id:
            raise ValueError("Target store must be different from current store.")

        comparison = CardService.compare_with_store(card, target_store_id, actor=actor)
        internal_matched = comparison['_internal_matched_items']

        if not internal_matched:
            raise ValueError(f"Cannot transfer memo: '{target_store.name}' does not carry any of the items from this memo.")

        if not omit_missing and comparison['missing_items_count'] > 0:
            raise ValueError(f"Target store does not carry {comparison['missing_items_count']} item(s) from your memo.")

        if clone:
            new_title = f"{card.title} ({target_store.name})"
            dest_card = Card.objects.create(
                user=card.user,
                store=target_store,
                vendor=target_store.vendor,
                title=new_title,
                shopping_mode=card.shopping_mode,
                notes=card.notes,
                budget_limit=card.budget_limit,
                is_saved_for_later=card.is_saved_for_later,
                planned_visit_date=card.planned_visit_date
            )
            for m in internal_matched:
                CardItem.objects.create(
                    card=dest_card,
                    product=m['target_product'],
                    quantity=Decimal(m['quantity']),
                    unit_price=Decimal(m['target_unit_price']),
                    is_picked=False
                )
            return dest_card
        else:
            card.store = target_store
            card.vendor = target_store.vendor
            card.coupon = None  # Reset store coupon bound to prior store
            card.save(update_fields=['store', 'vendor', 'coupon', 'updated_at'])

            matched_source_ids = {m['source_item_id'] for m in internal_matched}
            card.items.exclude(id__in=matched_source_ids).delete()

            for m in internal_matched:
                card.items.filter(id=m['source_item_id']).update(
                    product=m['target_product'],
                    unit_price=Decimal(m['target_unit_price']),
                    is_picked=False,
                    picked_at=None,
                    updated_at=timezone.now()
                )

            card.refresh_from_db()
            return card


