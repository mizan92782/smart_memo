import math
from decimal import Decimal
from typing import List, Optional, Tuple
from django.db import transaction
from stores.models.store_mod import Store
from stores.repositories.store_repository import StoreRepository


class StoreService:
    """Business operations for store management and nearby discovery."""

    @staticmethod
    def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates great-circle distance between two coordinates in kilometers using Haversine formula.
        """
        R = 6371.0  # Earth's radius in kilometers
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(R * c, 2)

    @staticmethod
    def discover_nearby_stores(
        lat: Optional[float],
        lng: Optional[float],
        radius_km: float = 10.0,
        max_limit: int = 50
    ) -> Tuple[List[Store], bool]:
        """
        Discovers active stores within radius_km sorted by distance ascending.
        Returns (stores_list, is_fallback).
        If lat or lng are None, gracefully falls back to returning all active stores without distance.
        """
        if lat is None or lng is None:
            # Fallback: non-location store browsing
            stores = list(StoreRepository.get_public_active_stores()[:max_limit])
            return stores, True

        # Validate coordinate boundaries
        if not (-90.0 <= lat <= 90.0):
            raise ValueError("Latitude must be between -90.0 and 90.0 degrees.")
        if not (-180.0 <= lng <= 180.0):
            raise ValueError("Longitude must be between -180.0 and 180.0 degrees.")
        if radius_km <= 0 or radius_km > 100.0:
            raise ValueError("Search radius must be between 0.1 and 100.0 kilometers.")

        # Bounding box rough filter for efficiency
        delta_lat = radius_km / 111.0
        cos_lat = math.cos(math.radians(lat))
        delta_lng = radius_km / (111.0 * cos_lat) if abs(cos_lat) > 0.001 else radius_km / 111.0

        candidates = Store.objects.filter(
            is_active=True,
            is_verified=True,
            is_deleted=False,
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__gte=Decimal(str(round(lat - delta_lat, 6))),
            latitude__lte=Decimal(str(round(lat + delta_lat, 6))),
            longitude__gte=Decimal(str(round(lng - delta_lng, 6))),
            longitude__lte=Decimal(str(round(lng + delta_lng, 6))),
        )

        results = []
        for store in candidates:
            dist = StoreService.calculate_haversine_distance(
                lat, lng, float(store.latitude), float(store.longitude)
            )
            if dist <= radius_km:
                store.distance_km = dist
                results.append(store)

        # Stable sort by distance ascending, then store ID
        results.sort(key=lambda s: (s.distance_km, s.id))
        return results[:max_limit], False

    @staticmethod
    @transaction.atomic
    def register_store(vendor, **store_data) -> Store:
        return StoreRepository.create_store(vendor=vendor, **store_data)

    @staticmethod
    def update_store_profile(store: Store, **update_data) -> Store:
        # Prevent reassigning vendor
        update_data.pop('vendor', None)
        update_data.pop('vendor_id', None)
        return StoreRepository.update_store(store, **update_data)

    @staticmethod
    def deactivate_store(store: Store) -> Store:
        store.is_active = False
        store.save(update_fields=['is_active'])
        return store

    @staticmethod
    def verify_store(store: Store, verified_by=None, notes: str = "") -> Store:
        """Approve and verify a store for platform visibility and orders."""
        from shared.caching.cache_service import CacheService
        from audit.services.audit_service import AuditService
        from audit.models.audit_mod import AuditAction
        updated = StoreRepository.verify_store(store, verified_by=verified_by, notes=notes)
        CacheService.invalidate_store_profile(store.id)
        CacheService.invalidate_catalog(store.id)
        AuditService.log(
            action=AuditAction.STORE_VERIFIED,
            target_model="Store",
            target_id=store.id,
            actor=verified_by,
            store=store,
            details={"notes": notes}
        )
        return updated

    @staticmethod
    def suspend_store(store: Store, reason: str = "", actor=None) -> Store:
        """Administrative suspension of a store."""
        from shared.caching.cache_service import CacheService
        from audit.services.audit_service import AuditService
        from audit.models.audit_mod import AuditAction
        updated = StoreRepository.suspend_store(store, reason=reason)
        CacheService.invalidate_store_profile(store.id)
        CacheService.invalidate_catalog(store.id)
        AuditService.log(
            action=AuditAction.STORE_SUSPENDED,
            target_model="Store",
            target_id=store.id,
            actor=actor,
            store=store,
            details={"reason": reason}
        )
        return updated

    @staticmethod
    def activate_store(store: Store, actor=None) -> Store:
        """Administrative reactivation of a suspended store."""
        from shared.caching.cache_service import CacheService
        from audit.services.audit_service import AuditService
        from audit.models.audit_mod import AuditAction
        updated = StoreRepository.activate_store(store)
        CacheService.invalidate_store_profile(store.id)
        CacheService.invalidate_catalog(store.id)
        AuditService.log(
            action=AuditAction.STORE_ACTIVATED,
            target_model="Store",
            target_id=store.id,
            actor=actor,
            store=store,
            details={}
        )
        return updated

    @staticmethod
    def get_platform_governance_overview() -> dict:
        """Retrieve aggregated platform metrics."""
        return StoreRepository.get_platform_metrics()


