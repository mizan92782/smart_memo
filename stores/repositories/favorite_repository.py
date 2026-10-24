from typing import Optional, Tuple
from django.db.models import QuerySet
from stores.models.favorite_mod import FavoriteStore
from stores.models.store_mod import Store


class FavoriteRepository:
    """Handles pure database queries for FavoriteStore entity (static methods only)."""

    @staticmethod
    def get_by_customer(customer_id: int) -> QuerySet[FavoriteStore]:
        return FavoriteStore.objects.filter(
            customer_id=customer_id,
            is_deleted=False,
            store__is_deleted=False,
            store__is_active=True
        ).select_related('store', 'store__vendor')

    @staticmethod
    def get_favorite(customer_id: int, store_id: int) -> Optional[FavoriteStore]:
        return FavoriteStore.objects.filter(
            customer_id=customer_id,
            store_id=store_id,
            is_deleted=False
        ).first()

    @staticmethod
    def is_favorite(customer_id: int, store_id: int) -> bool:
        return FavoriteStore.objects.filter(
            customer_id=customer_id,
            store_id=store_id,
            is_deleted=False
        ).exists()

    @staticmethod
    def add_favorite(customer, store: Store) -> Tuple[FavoriteStore, bool]:
        """Idempotently add store to customer favorites."""
        fav, created = FavoriteStore.objects.get_or_create(
            customer=customer,
            store=store,
            defaults={'is_deleted': False}
        )
        if not created and fav.is_deleted:
            fav.restore()
            created = True
        return fav, created

    @staticmethod
    def remove_favorite(customer, store: Store) -> bool:
        """Removes store from customer favorites if it exists."""
        fav = FavoriteStore.objects.filter(
            customer=customer,
            store=store,
            is_deleted=False
        ).first()
        if fav:
            fav.delete()
            return True
        return False
