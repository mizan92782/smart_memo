from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from inventory.models.batch_mod import ProductBatch, BatchStatus
from inventory.serializers.batch_ser import (
    ProductBatchSerializer,
    ProductBatchCreateSerializer,
    BatchDisposalSerializer,
    BatchClearanceSerializer,
    FEFOAllocationSerializer
)
from inventory.services.batch_service import BatchService
from products.models.product_mod import Product
from stores.models.store_mod import Store
from shared.permissions.permissions import IsVendor
from shared.responses.responses import custome_success_response, custome_error_response
from django.utils import timezone


def _format_error(e):
    """Normalize DRF ValidationError or Python ValueError into a readable string message."""
    if hasattr(e, 'detail'):
        detail = e.detail
        if isinstance(detail, list) and detail:
            return str(detail[0])
        elif isinstance(detail, dict) and detail:
            first_val = next(iter(detail.values()))
            if isinstance(first_val, list) and first_val:
                return str(first_val[0])
            return str(first_val)
        return str(detail)
    return str(e)


class ProductBatchViewSet(viewsets.ModelViewSet):
    """
    ViewSet for perishable product batch management, FEFO allocations,
    spoilage write-offs, clearance pricing, and near-expiry alerting.
    Enforces strict server-side tenant isolation.
    """
    serializer_class = ProductBatchSerializer
    permission_classes = [IsAuthenticated, IsVendor]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            qs = ProductBatch.objects.all()
        else:
            vendor_stores = user.stores.values_list('id', flat=True)
            qs = ProductBatch.objects.filter(store_id__in=vendor_stores)

        qs = qs.select_related('store', 'product')

        store_id = self.request.query_params.get('store_id')
        if store_id:
            qs = qs.filter(store_id=int(store_id))

        product_id = self.request.query_params.get('product_id')
        if product_id:
            qs = qs.filter(product_id=int(product_id))

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        is_clearance = self.request.query_params.get('is_clearance')
        if is_clearance is not None:
            qs = qs.filter(is_clearance=is_clearance.lower() in ('true', '1'))

        is_expired = self.request.query_params.get('is_expired')
        if is_expired is not None:
            today = timezone.now().date()
            if is_expired.lower() in ('true', '1'):
                qs = qs.filter(expiry_date__lt=today)
            else:
                qs = qs.filter(expiry_date__gte=today)

        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(batch_number__icontains=search) |
                Q(product__name__icontains=search) |
                Q(product__sku__icontains=search)
            )

        return qs.order_by('expiry_date', 'created_at')

    def create(self, request, *args, **kwargs):
        """Register a new perishable product batch."""
        serializer = ProductBatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        product = Product.objects.filter(pk=data['product_id'], is_deleted=False).select_related('store').first()
        if not product or not product.store:
            return custome_error_response("Product not found.", status_code=status.HTTP_404_NOT_FOUND)

        if product.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response(
                "You do not have permission to manage batches for this product's store.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        try:
            batch = BatchService.create_batch(
                store=product.store,
                product=product,
                batch_number=data['batch_number'],
                expiry_date=data['expiry_date'],
                initial_quantity=data['initial_quantity'],
                cost_price=data.get('cost_price', Decimal('0.00')),
                manufacture_date=data.get('manufacture_date'),
                add_to_stock=data.get('add_to_stock', False),
                actor=request.user,
                notes=data.get('notes', '')
            )
        except (ValidationError, ValueError) as e:
            return custome_error_response(_format_error(e), status_code=status.HTTP_400_BAD_REQUEST)

        return custome_success_response(
            message=f"Product batch '{batch.batch_number}' registered successfully.",
            data=ProductBatchSerializer(batch).data,
            status_code=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def dispose(self, request, pk=None):
        """Write off spoiled or expired stock from a batch."""
        batch = self.get_object()
        serializer = BatchDisposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = BatchService.dispose_batch(
                batch_id=batch.id,
                quantity=serializer.validated_data.get('quantity'),
                reason=serializer.validated_data.get('reason', 'Expired / Spoilage'),
                actor=request.user,
                notes=serializer.validated_data.get('notes', '')
            )
        except (ValidationError, ValueError) as e:
            return custome_error_response(_format_error(e), status_code=status.HTTP_400_BAD_REQUEST)

        return custome_success_response(
            message="Batch stock disposed successfully.",
            data=result,
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def clearance(self, request, pk=None):
        """Apply or update clearance discount on a batch."""
        batch = self.get_object()
        serializer = BatchClearanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_batch = BatchService.set_clearance(
                batch_id=batch.id,
                discount_percent=serializer.validated_data['discount_percent'],
                actor=request.user
            )
        except (ValidationError, ValueError) as e:
            return custome_error_response(_format_error(e), status_code=status.HTTP_400_BAD_REQUEST)

        return custome_success_response(
            message="Batch clearance pricing updated.",
            data=ProductBatchSerializer(updated_batch).data,
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='near-expiry')
    def near_expiry(self, request):
        """List batches nearing expiry or already expired, triggering vendor notification."""
        user = request.user
        store_id = request.query_params.get('store_id')
        if store_id:
            store = Store.objects.filter(pk=int(store_id), vendor=user).first()
            if not store and not user.is_superuser:
                return custome_error_response("Store not found or unauthorized.", status_code=status.HTTP_404_NOT_FOUND)
        else:
            store = user.stores.first()
            if not store:
                return custome_error_response("No store found for current vendor.", status_code=status.HTTP_404_NOT_FOUND)

        days_threshold = int(request.query_params.get('days_threshold', 7))
        expiring = BatchService.scan_and_alert_expiring_batches(
            store=store,
            days_threshold=days_threshold,
            actor=request.user
        )

        return custome_success_response(
            message=f"Found {len(expiring)} batch(es) nearing expiry within {days_threshold} days.",
            data=expiring,
            status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='fefo-allocate')
    def fefo_allocate(self, request):
        """Simulate or execute FEFO stock allocation for a product."""
        serializer = FEFOAllocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        product = Product.objects.filter(pk=data['product_id'], is_deleted=False).select_related('store').first()
        if not product or not product.store:
            return custome_error_response("Product not found.", status_code=status.HTTP_404_NOT_FOUND)

        if product.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response(
                "You do not have permission to allocate batches for this product's store.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        try:
            allocation = BatchService.allocate_fefo(
                store=product.store,
                product=product,
                quantity=data['quantity'],
                deduct=data.get('deduct', True)
            )
        except (ValidationError, ValueError) as e:
            return custome_error_response(_format_error(e), status_code=status.HTTP_400_BAD_REQUEST)

        return custome_success_response(
            message="FEFO allocation calculated successfully.",
            data=allocation,
            status_code=status.HTTP_200_OK
        )
