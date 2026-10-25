from decimal import Decimal
from typing import Optional, Dict, Any, List
from django.db import transaction
from django.core.exceptions import PermissionDenied, ValidationError
from stores.models.store_mod import Store
from products.models.product_mod import Product
from cards.models.card_mod import Card, CardItem, ShoppingMode
from cards.models.template_mod import StoreMemoTemplate, StoreMemoTemplateItem
from cards.repositories.template_repository import TemplateRepository
from cards.repositories.card_repository import CardRepository


class TemplateService:
    """Business service orchestrating Store Routine Shopping Templates and One-Tap Memo Hydration."""

    @staticmethod
    @transaction.atomic
    def save_memo_as_template(
        card: Card,
        user,
        name: str,
        description: str = '',
        is_favorite: bool = False
    ) -> StoreMemoTemplate:
        """Saves current shopping memo line items into a named routine template for the store."""
        if card.user_id != user.id and not getattr(user, 'is_staff', False):
            raise PermissionDenied("You can only save your own shopping memo as a template.")

        if not card.store_id:
            raise ValidationError("Shopping memo must be bound to a store to create a store template.")

        items = list(card.items.select_related('product').all())
        if not items:
            raise ValidationError("Cannot create a routine template from an empty shopping memo.")

        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("Template name cannot be blank.")

        # Check for existing template with same name for this store and user
        template = StoreMemoTemplate.objects.filter(
            user=user,
            store=card.store,
            name__iexact=clean_name,
            is_deleted=False
        ).first()

        if template:
            template.description = description.strip()
            template.is_favorite = is_favorite
            template.shopping_mode = card.shopping_mode
            template.save(update_fields=['description', 'is_favorite', 'shopping_mode', 'updated_at'])
            # Clear previous items to overwrite
            TemplateRepository.clear_items(template)
        else:
            template = TemplateRepository.create_template(
                user=user,
                store=card.store,
                name=clean_name,
                description=description,
                shopping_mode=card.shopping_mode,
                is_favorite=is_favorite
            )

        for card_item in items:
            if card_item.product and not card_item.product.is_deleted:
                TemplateRepository.add_or_update_item(
                    template=template,
                    product=card_item.product,
                    quantity=card_item.quantity
                )

        return template

    @staticmethod
    def create_template(
        user,
        store_id: int,
        name: str,
        description: str = '',
        shopping_mode: str = 'remote',
        is_favorite: bool = False
    ) -> StoreMemoTemplate:
        store = Store.objects.filter(id=store_id, is_deleted=False).first()
        if not store:
            raise ValidationError("Store not found.")

        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("Template name cannot be blank.")

        if StoreMemoTemplate.objects.filter(user=user, store=store, name__iexact=clean_name, is_deleted=False).exists():
            raise ValidationError(f"A routine template named '{clean_name}' already exists for {store.name}.")

        return TemplateRepository.create_template(
            user=user,
            store=store,
            name=clean_name,
            description=description,
            shopping_mode=shopping_mode,
            is_favorite=is_favorite
        )

    @staticmethod
    def update_template(template: StoreMemoTemplate, user, **fields) -> StoreMemoTemplate:
        if template.user_id != user.id and not getattr(user, 'is_staff', False):
            raise PermissionDenied("You do not have permission to modify this template.")
        return TemplateRepository.update_template(template, **fields)

    @staticmethod
    def delete_template(template: StoreMemoTemplate, user) -> None:
        if template.user_id != user.id and not getattr(user, 'is_staff', False):
            raise PermissionDenied("You do not have permission to delete this template.")
        template.is_deleted = True
        template.save(update_fields=['is_deleted', 'updated_at'])

    @staticmethod
    def add_item_to_template(
        template: StoreMemoTemplate,
        user,
        product_id: int,
        quantity: Decimal = Decimal('1.000'),
        notes: str = ''
    ) -> StoreMemoTemplateItem:
        if template.user_id != user.id and not getattr(user, 'is_staff', False):
            raise PermissionDenied("You do not have permission to edit this template.")

        product = Product.objects.filter(id=product_id, is_deleted=False).first()
        if not product:
            raise ValidationError("Product not found.")

        if product.store_id != template.store_id:
            raise ValidationError(f"Product '{product.name}' does not belong to {template.store.name}.")

        if quantity <= Decimal('0.000'):
            raise ValidationError("Quantity must be greater than zero.")

        return TemplateRepository.add_or_update_item(
            template=template,
            product=product,
            quantity=quantity,
            notes=notes
        )

    @staticmethod
    def remove_item_from_template(template: StoreMemoTemplate, user, item_id: int) -> bool:
        if template.user_id != user.id and not getattr(user, 'is_staff', False):
            raise PermissionDenied("You do not have permission to edit this template.")
        return TemplateRepository.remove_item(template, item_id)

    @staticmethod
    @transaction.atomic
    def load_template_to_memo(
        template: StoreMemoTemplate,
        user,
        mode: str = 'replace',
        shopping_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        One-Tap Memo Hydration:
        Loads items from this routine template into the customer's active draft shopping memo for the store.
        Re-validates catalog availability, live stock, and effective pricing.
        """
        if template.user_id != user.id and not getattr(user, 'is_staff', False):
            raise PermissionDenied("You do not have permission to load this template.")

        store = template.store
        if not store.is_active:
            raise ValidationError(f"Store '{store.name}' is currently inactive.")

        # Find or create active draft memo for this store
        card = CardRepository.get_active_card_for_user(user_id=user.id, store_id=store.id)
        if not card:
            card = Card.objects.create(
                user=user,
                store=store,
                vendor=store.vendor,
                shopping_mode=shopping_mode or template.shopping_mode or ShoppingMode.REMOTE,
                title=f"{store.name} Memo"
            )
        else:
            if shopping_mode:
                card.shopping_mode = shopping_mode
                card.save(update_fields=['shopping_mode', 'updated_at'])

        if mode == 'replace':
            card.items.all().delete()

        template_items = list(template.items.select_related('product', 'product__stock_balance').all())
        loaded_items = []
        omitted_items = []

        for t_item in template_items:
            prod = t_item.product
            if not prod or prod.is_deleted or not prod.is_active:
                omitted_items.append({
                    'product_id': prod.id if prod else None,
                    'product_name': prod.name if prod else 'Unknown Product',
                    'reason': 'Product no longer available in store catalog'
                })
                continue

            balance = getattr(prod, 'stock_balance', None)
            available = (balance.on_hand - balance.reserved) if balance else Decimal('0.000')
            if available <= Decimal('0.000'):
                omitted_items.append({
                    'product_id': prod.id,
                    'product_name': prod.name,
                    'reason': 'Product currently out of stock'
                })
                continue

            qty_to_add = t_item.quantity
            # Clamp to available stock if needed, or fulfill requested quantity
            final_qty = min(qty_to_add, available)

            fresh_unit_price = prod.effective_price

            if mode == 'merge':
                card_item = card.items.filter(product=prod).first()
                if card_item:
                    new_qty = min(card_item.quantity + qty_to_add, available)
                    card_item.quantity = new_qty
                    card_item.unit_price = fresh_unit_price
                    card_item.save(update_fields=['quantity', 'unit_price', 'updated_at'])
                else:
                    card_item = CardItem.objects.create(
                        card=card,
                        product=prod,
                        quantity=final_qty,
                        unit_price=fresh_unit_price
                    )
            else:
                card_item = CardItem.objects.create(
                    card=card,
                    product=prod,
                    quantity=final_qty,
                    unit_price=fresh_unit_price
                )

            loaded_items.append({
                'item_id': card_item.id,
                'product_id': prod.id,
                'product_name': prod.name,
                'quantity': str(card_item.quantity),
                'unit_price': str(card_item.unit_price),
                'subtotal': str(card_item.subtotal),
                'aisle': prod.aisle,
                'shelf_location': prod.shelf_location
            })

        card.refresh_from_db()

        return {
            'card': card,
            'loaded_items_count': len(loaded_items),
            'omitted_items_count': len(omitted_items),
            'loaded_items': loaded_items,
            'omitted_items': omitted_items
        }
