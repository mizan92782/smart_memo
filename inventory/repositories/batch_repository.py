from datetime import timedelta
from decimal import Decimal
from typing import Optional
from django.db.models import QuerySet, Q
from django.utils import timezone
from inventory.models.batch_mod import ProductBatch, BatchStatus
from stores.models.store_mod import Store
from products.models.product_mod import Product


class BatchRepository:
    """Repository handling data access and FEFO query ordering for product batches."""

    @staticmethod
    def get_by_id(batch_id: int, store: Optional[Store] = None, lock: bool = False) -> Optional[ProductBatch]:
        """Fetch batch by ID with optional tenant store filter and pessimistic locking."""
        qs = ProductBatch.objects.select_related('store', 'product')
        if lock:
            qs = qs.select_for_update()
        if store:
            qs = qs.filter(store=store)
        return qs.filter(id=batch_id).first()

    @staticmethod
    def list_batches(
        store: Store,
        product: Optional[Product] = None,
        status: Optional[str] = None,
        is_clearance: Optional[bool] = None,
        search: Optional[str] = None
    ) -> QuerySet[ProductBatch]:
        """List store batches with optional filters and search."""
        qs = ProductBatch.objects.filter(store=store).select_related('product', 'store')
        if product:
            qs = qs.filter(product=product)
        if status:
            qs = qs.filter(status=status)
        if is_clearance is not None:
            qs = qs.filter(is_clearance=is_clearance)
        if search:
            qs = qs.filter(
                Q(batch_number__icontains=search) |
                Q(product__name__icontains=search) |
                Q(product__sku__icontains=search)
            )
        return qs.order_by('expiry_date', 'created_at')

    @staticmethod
    def get_fefo_candidates(
        store: Store,
        product: Product,
        reference_date=None,
        lock: bool = True
    ) -> QuerySet[ProductBatch]:
        """
        Retrieve candidate batches in FEFO order (earliest expiry first).
        Only includes non-disposed batches with current_quantity > 0 and expiry_date >= reference_date.
        """
        ref_date = reference_date or timezone.now().date()
        qs = ProductBatch.objects.filter(
            store=store,
            product=product,
            current_quantity__gt=Decimal('0.000'),
            expiry_date__gte=ref_date
        ).exclude(
            status__in=[BatchStatus.DISPOSED, BatchStatus.DEPLETED]
        )
        if lock:
            qs = qs.select_for_update()
        return qs.order_by('expiry_date', 'created_at')

    @staticmethod
    def get_near_expiry_batches(
        store: Store,
        days_threshold: int = 7,
        reference_date=None
    ) -> QuerySet[ProductBatch]:
        """Retrieve active batches expiring within days_threshold from reference_date."""
        ref_date = reference_date or timezone.now().date()
        cutoff_date = ref_date + timedelta(days=days_threshold)
        return ProductBatch.objects.filter(
            store=store,
            current_quantity__gt=Decimal('0.000'),
            expiry_date__gte=ref_date,
            expiry_date__lte=cutoff_date
        ).exclude(
            status=BatchStatus.DISPOSED
        ).select_related('product').order_by('expiry_date', 'created_at')

    @staticmethod
    def get_expired_batches(
        store: Store,
        reference_date=None
    ) -> QuerySet[ProductBatch]:
        """Retrieve batches whose expiry_date is in the past and still have quantity on-hand."""
        ref_date = reference_date or timezone.now().date()
        return ProductBatch.objects.filter(
            store=store,
            current_quantity__gt=Decimal('0.000'),
            expiry_date__lt=ref_date
        ).exclude(
            status=BatchStatus.DISPOSED
        ).select_related('product').order_by('expiry_date')
