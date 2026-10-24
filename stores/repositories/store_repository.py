from typing import Optional, Dict, Any
from decimal import Decimal
from django.db.models import QuerySet, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from stores.models.store_mod import Store
from users.models.user_mod import User
from orders.models.order_mod import Order, OrderStatus
from shared.enums.enums import UserRoleEnum


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
        """Fetch only non-deleted, active and verified stores for public customer discovery."""
        return Store.objects.filter(is_active=True, is_verified=True, is_deleted=False)

    @staticmethod
    def get_all_stores(include_deleted: bool = False) -> QuerySet[Store]:
        """Fetch all platform stores for staff/admin governance."""
        qs = Store.objects.all() if include_deleted else Store.objects.filter(is_deleted=False)
        return qs.select_related('vendor')

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
    def verify_store(store: Store, verified_by: Optional[User] = None, notes: str = "") -> Store:
        """Mark a store as verified by platform administration."""
        store.is_verified = True
        store.verified_at = timezone.now()
        if notes:
            store.verification_notes = notes
        store.save(update_fields=['is_verified', 'verified_at', 'verification_notes'])
        return store

    @staticmethod
    def suspend_store(store: Store, reason: str = "") -> Store:
        """Suspend a store, immediately disabling public discovery and orders."""
        store.is_active = False
        if reason:
            store.verification_notes = reason
        store.save(update_fields=['is_active', 'verification_notes'])
        return store

    @staticmethod
    def activate_store(store: Store) -> Store:
        """Reactivate a suspended store."""
        store.is_active = True
        store.save(update_fields=['is_active'])
        return store

    @staticmethod
    def delete_store(store: Store) -> None:
        store.soft_delete()

    @staticmethod
    def get_platform_metrics() -> Dict[str, Any]:
        """
        Aggregate platform-wide business and operational metrics for platform administration.
        Uses efficient SQL COUNT/SUM queries rather than memory loops.
        """
        total_stores = Store.objects.filter(is_deleted=False).count()
        active_stores = Store.objects.filter(is_deleted=False, is_active=True).count()
        verified_stores = Store.objects.filter(is_deleted=False, is_verified=True).count()
        unverified_stores = Store.objects.filter(is_deleted=False, is_verified=False).count()
        suspended_stores = Store.objects.filter(is_deleted=False, is_active=False).count()

        total_vendors = User.objects.filter(role=UserRoleEnum.VENDOR).count()
        total_customers = User.objects.filter(role__in=[UserRoleEnum.CUSTOMER, UserRoleEnum.USER]).count()
        total_staff = User.objects.filter(role__in=[UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER]).count()

        total_orders = Order.objects.count()
        completed_orders = Order.objects.filter(status=OrderStatus.COMPLETED).count()
        active_orders = Order.objects.filter(
            status__in=[
                OrderStatus.SUBMITTED,
                OrderStatus.ACCEPTED,
                OrderStatus.PREPARING,
                OrderStatus.READY_FOR_PICKUP,
                OrderStatus.OUT_FOR_DELIVERY,
            ]
        ).count()
        cancelled_orders = Order.objects.filter(status=OrderStatus.CANCELLED).count()

        gmv_agg = Order.objects.filter(status=OrderStatus.COMPLETED).aggregate(
            gmv=Coalesce(Sum('total_amount'), Decimal('0.00'))
        )
        gross_merchandise_volume = gmv_agg['gmv']

        return {
            "stores": {
                "total": total_stores,
                "active": active_stores,
                "verified": verified_stores,
                "unverified": unverified_stores,
                "suspended": suspended_stores,
            },
            "users": {
                "total_vendors": total_vendors,
                "total_customers": total_customers,
                "total_staff": total_staff,
            },
            "orders": {
                "total": total_orders,
                "completed": completed_orders,
                "active": active_orders,
                "cancelled": cancelled_orders,
                "gross_merchandise_volume": str(gross_merchandise_volume),
            }
        }

