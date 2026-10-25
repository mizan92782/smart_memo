from decimal import Decimal
from typing import Optional
from django.db.models import QuerySet
from cards.models.template_mod import StoreMemoTemplate, StoreMemoTemplateItem


class TemplateRepository:
    """Repository handling database query operations for Store Routine Memo Templates."""

    @staticmethod
    def get_by_id(template_id: int) -> Optional[StoreMemoTemplate]:
        return StoreMemoTemplate.objects.filter(
            pk=template_id,
            is_deleted=False
        ).select_related('store', 'user', 'vendor').prefetch_related(
            'items__product',
            'items__product__category',
            'items__product__stock_balance'
        ).first()

    @staticmethod
    def get_by_user(user_id: int, store_id: Optional[int] = None, is_favorite: Optional[bool] = None) -> QuerySet[StoreMemoTemplate]:
        qs = StoreMemoTemplate.objects.filter(
            user_id=user_id,
            is_deleted=False
        ).select_related('store', 'vendor').prefetch_related(
            'items__product',
            'items__product__category',
            'items__product__stock_balance'
        )
        if store_id is not None:
            qs = qs.filter(store_id=store_id)
        if is_favorite is not None:
            qs = qs.filter(is_favorite=is_favorite)
        return qs.order_by('-is_favorite', '-created_at')

    @staticmethod
    def get_for_user(user_id: int, store_id: Optional[int] = None, is_favorite: Optional[bool] = None) -> QuerySet[StoreMemoTemplate]:
        return TemplateRepository.get_by_user(user_id=user_id, store_id=store_id, is_favorite=is_favorite)

    @staticmethod
    def get_by_vendor(vendor_id: int, store_id: Optional[int] = None) -> QuerySet[StoreMemoTemplate]:
        qs = StoreMemoTemplate.objects.filter(
            vendor_id=vendor_id,
            is_deleted=False
        ).select_related('store', 'user', 'vendor').prefetch_related(
            'items__product',
            'items__product__category',
            'items__product__stock_balance'
        )
        if store_id is not None:
            qs = qs.filter(store_id=store_id)
        return qs.order_by('-created_at')

    @staticmethod
    def create_template(
        user,
        store,
        name: str,
        description: str = '',
        shopping_mode: str = 'remote',
        is_favorite: bool = False
    ) -> StoreMemoTemplate:
        vendor = getattr(store, 'vendor', None)
        return StoreMemoTemplate.objects.create(
            user=user,
            store=store,
            vendor=vendor,
            name=name.strip(),
            description=description.strip(),
            shopping_mode=shopping_mode,
            is_favorite=is_favorite
        )

    @staticmethod
    def update_template(template: StoreMemoTemplate, **fields) -> StoreMemoTemplate:
        update_fields = []
        for key, value in fields.items():
            if hasattr(template, key) and value is not None:
                setattr(template, key, value)
                update_fields.append(key)
        if update_fields:
            if 'updated_at' not in update_fields:
                update_fields.append('updated_at')
            template.save(update_fields=update_fields)
        return template

    @staticmethod
    def add_or_update_item(
        template: StoreMemoTemplate,
        product,
        quantity: Decimal,
        notes: str = ''
    ) -> StoreMemoTemplateItem:
        item, created = StoreMemoTemplateItem.objects.get_or_create(
            template=template,
            product=product,
            defaults={'quantity': quantity, 'notes': notes}
        )
        if not created:
            item.quantity = quantity
            if notes:
                item.notes = notes
            item.save(update_fields=['quantity', 'notes', 'updated_at'])
        return item

    @staticmethod
    def remove_item(template: StoreMemoTemplate, item_id: int) -> bool:
        deleted_count, _ = StoreMemoTemplateItem.objects.filter(
            id=item_id,
            template=template
        ).delete()
        return deleted_count > 0

    @staticmethod
    def clear_items(template: StoreMemoTemplate) -> None:
        template.items.all().delete()
