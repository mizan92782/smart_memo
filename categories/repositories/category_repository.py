from typing import Optional
from django.db.models import QuerySet
from categories.models.category_mod import Category
from stores.models.store_mod import Store


class CategoryRepository:
    """Handles all database operations for the Category model."""

    @staticmethod
    def get_all() -> QuerySet[Category]:
        return Category.objects.filter(is_deleted=False).order_by('name')

    @staticmethod
    def get_by_store(store_id: int) -> QuerySet[Category]:
        return Category.objects.filter(store_id=store_id, is_deleted=False).order_by('name')

    @staticmethod
    def get_all_with_products() -> QuerySet[Category]:
        return Category.objects.filter(is_deleted=False).prefetch_related('products').order_by('name')

    @staticmethod
    def get_by_id(category_id: int) -> Optional[Category]:
        return Category.objects.filter(pk=category_id, is_deleted=False).first()

    @staticmethod
    def get_by_name(name: str, store_id: Optional[int] = None) -> Optional[Category]:
        qs = Category.objects.filter(name__iexact=name, is_deleted=False)
        if store_id is not None:
            qs = qs.filter(store_id=store_id)
        return qs.first()

    @staticmethod
    def create_category(name: str, store: Optional[Store] = None) -> Category:
        return Category.objects.create(name=name, store=store)

    @staticmethod
    def update_category(category: Category, name: str) -> Category:
        category.name = name
        category.save()
        return category

    @staticmethod
    def delete_category(category: Category) -> None:
        category.soft_delete()
