from typing import Optional
from django.db.models import QuerySet
from stores.models.store_mod import Store


class StoreRepository:
    """Handles database queries for the Store model (static methods only)."""

    @staticmethod
    def get_by_id(store_id: int) -> Optional[Store]:
        return Store.objects.filter(pk=store_id, is_deleted=False).first()

    @staticmethod
    def get_by_vendor(vendor_id: int) -> QuerySet[Store]:
        return Store.objects.filter(vendor_id=vendor_id, is_deleted=False)

    @staticmethod
    def get_public_active_stores() -> QuerySet[Store]:
        return Store.objects.filter(is_active=True, is_deleted=False)

    @staticmethod
    def create_store(vendor, **kwargs) -> Store:
        return Store.objects.create(vendor=vendor, **kwargs)

    @staticmethod
    def update_store(store: Store, **kwargs) -> Store:
        for key, value in kwargs.items():
            setattr(store, key, value)
        store.save()
        return store

    @staticmethod
    def delete_store(store: Store) -> None:
        store.soft_delete()
