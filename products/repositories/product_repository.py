from typing import Optional
from django.db.models import QuerySet, Q
from products.models.product_mod import Product


class ProductRepository:
    """Handles all database operations for the Product model."""

    @staticmethod
    def get_all() -> QuerySet[Product]:
        return Product.objects.filter(is_deleted=False).select_related('category', 'store').order_by('name')

    @staticmethod
    def get_by_store(store_id: int) -> QuerySet[Product]:
        return Product.objects.filter(store_id=store_id, is_deleted=False).select_related('category', 'store').order_by('name')

    @staticmethod
    def get_by_id(product_id: int) -> Optional[Product]:
        return Product.objects.filter(pk=product_id, is_deleted=False).select_related('category', 'store').first()

    @staticmethod
    def get_by_category_id(category_id: int) -> QuerySet[Product]:
        return Product.objects.filter(category_id=category_id, is_deleted=False).select_related('store').order_by('name')

    @staticmethod
    def get_in_stock() -> QuerySet[Product]:
        return Product.objects.filter(stock__gt=0, is_deleted=False, is_active=True).select_related('category', 'store').order_by('name')

    @staticmethod
    def search_catalog(query: str = None, store_id: int = None, category_id: int = None) -> QuerySet[Product]:
        qs = Product.objects.filter(is_deleted=False, is_active=True, store__is_active=True).select_related('category', 'store')
        if store_id:
            qs = qs.filter(store_id=store_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if query:
            qs = qs.filter(
                Q(name__icontains=query) |
                Q(second_name__icontains=query) |
                Q(sku__icontains=query) |
                Q(barcode__icontains=query) |
                Q(tags__contains=[query])
            )
        return qs.order_by('name')

    @staticmethod
    def get_by_barcode_or_sku(store_id: int, code: str) -> Optional[Product]:
        """Fetch active store product by exact barcode or SKU."""
        if not code or not str(code).strip():
            return None
        c = str(code).strip()
        return Product.objects.filter(
            store_id=store_id,
            is_deleted=False,
            is_active=True
        ).filter(
            Q(barcode__iexact=c) | Q(sku__iexact=c)
        ).select_related('category', 'store').first()

    @staticmethod
    def create_product(**kwargs) -> Product:
        return Product.objects.create(**kwargs)

    @staticmethod
    def update_product(product: Product, **kwargs) -> Product:
        for field, value in kwargs.items():
            setattr(product, field, value)
        product.save()
        return product

    @staticmethod
    def delete_product(product: Product) -> None:
        product.soft_delete()
