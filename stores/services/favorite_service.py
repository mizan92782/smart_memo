from django.db.models import QuerySet
from stores.models.favorite_mod import FavoriteStore
from stores.models.store_mod import Store
from stores.repositories.favorite_repository import FavoriteRepository
from stores.repositories.store_repository import StoreRepository


class FavoriteService:
    """Encapsulates business operations for customer favorite stores."""

    @staticmethod
    def add_store_to_favorites(customer, store_id: int) -> FavoriteStore:
        store = StoreRepository.get_by_id(store_id)
        if not store or not store.is_active:
            raise ValueError("Store not found or is currently inactive.")

        fav, _ = FavoriteRepository.add_favorite(customer=customer, store=store)
        return fav

    @staticmethod
    def remove_store_from_favorites(customer, store_id: int) -> bool:
        store = StoreRepository.get_by_id(store_id)
        if not store:
            raise ValueError("Store not found.")

        return FavoriteRepository.remove_favorite(customer=customer, store=store)

    @staticmethod
    def get_customer_favorites(customer) -> QuerySet[FavoriteStore]:
        return FavoriteRepository.get_by_customer(customer.id)

    @staticmethod
    def is_store_favorite(customer, store_id: int) -> bool:
        if not customer or not customer.is_authenticated:
            return False
        return FavoriteRepository.is_favorite(customer_id=customer.id, store_id=store_id)
