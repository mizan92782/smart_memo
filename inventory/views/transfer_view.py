from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from inventory.models.transfer_mod import StockTransfer
from inventory.serializers.transfer_ser import (
    StockTransferSerializer,
    StockTransferCreateSerializer,
    StockTransferReceiveSerializer,
    StockTransferCancelSerializer
)
from inventory.services.stock_transfer_service import StockTransferService
from shared.permissions.permissions import IsVendor
from shared.responses.responses import custome_success_response, custome_error_response


class StockTransferViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for inter-store stock transfer management:
    Creation, dispatch, destination receiving, cancellation, and thermal driver waybill generation.
    """
    serializer_class = StockTransferSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return StockTransfer.objects.none()

        base_qs = (
            StockTransfer.objects
            .filter(is_deleted=False)
            .select_related('vendor', 'source_store', 'destination_store', 'received_by')
            .prefetch_related('items__source_product', 'items__destination_product')
        )

        if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
            qs = base_qs
        else:
            vendor_stores = user.stores.values_list('id', flat=True)
            from django.db.models import Q
            qs = base_qs.filter(Q(vendor=user) | Q(source_store_id__in=vendor_stores) | Q(destination_store_id__in=vendor_stores))

        # Query Filters
        source_id = self.request.query_params.get('source_store_id')
        if source_id:
            qs = qs.filter(source_store_id=source_id)

        destination_id = self.request.query_params.get('destination_store_id')
        if destination_id:
            qs = qs.filter(destination_store_id=destination_id)

        transfer_status = self.request.query_params.get('status')
        if transfer_status:
            qs = qs.filter(status=transfer_status.lower())

        return qs

    @action(detail=False, methods=['post'], url_path='create-transfer')
    def create_transfer(self, request):
        """Vendor creates a new draft inter-store stock transfer."""
        serializer = StockTransferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            transfer = StockTransferService.create_transfer(
                vendor=request.user,
                source_store_id=serializer.validated_data['source_store_id'],
                destination_store_id=serializer.validated_data['destination_store_id'],
                items_data=serializer.validated_data['items'],
                tracking_notes=serializer.validated_data.get('tracking_notes', ''),
                driver_name=serializer.validated_data.get('driver_name', ''),
                driver_phone=serializer.validated_data.get('driver_phone', ''),
                vehicle_type=serializer.validated_data.get('vehicle_type', '')
            )
            data = StockTransferSerializer(transfer).data
            return custome_success_response(
                message=f"Stock transfer {transfer.transfer_number} created successfully.",
                data=data,
                status_code=status.HTTP_201_CREATED
            )
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='dispatch')
    def dispatch_transfer(self, request, pk=None):
        """Dispatches transfer into transit, deducting stock from source store with row locks."""
        transfer = StockTransfer.objects.filter(pk=pk, is_deleted=False).select_related('source_store', 'destination_store', 'vendor').first()
        if not transfer:
            return custome_error_response("Stock transfer not found.", status_code=status.HTTP_404_NOT_FOUND)

        try:
            dispatched = StockTransferService.dispatch_transfer(transfer, request.user)
            data = StockTransferSerializer(dispatched).data
            return custome_success_response(
                message=f"Stock transfer {dispatched.transfer_number} dispatched into transit.",
                data=data
            )
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='receive')
    def receive_transfer(self, request, pk=None):
        """Receives transit stock at destination store, provisioning matching products and crediting inventory."""
        transfer = StockTransfer.objects.filter(pk=pk, is_deleted=False).select_related('source_store', 'destination_store', 'vendor').first()
        if not transfer:
            return custome_error_response("Stock transfer not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = StockTransferReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            received = StockTransferService.receive_transfer(
                transfer=transfer,
                actor=request.user,
                items_received=serializer.validated_data.get('items', [])
            )
            data = StockTransferSerializer(received).data
            return custome_success_response(
                message=f"Stock transfer {received.transfer_number} received into {received.destination_store.name}.",
                data=data
            )
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel_transfer(self, request, pk=None):
        """Cancels a stock transfer (restores source stock if in transit)."""
        transfer = StockTransfer.objects.filter(pk=pk, is_deleted=False).select_related('source_store', 'destination_store', 'vendor').first()
        if not transfer:
            return custome_error_response("Stock transfer not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = StockTransferCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cancelled = StockTransferService.cancel_transfer(
                transfer=transfer,
                actor=request.user,
                reason=serializer.validated_data.get('reason', '')
            )
            data = StockTransferSerializer(cancelled).data
            return custome_success_response(
                message=f"Stock transfer {cancelled.transfer_number} cancelled.",
                data=data
            )
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='waybill')
    def waybill(self, request, pk=None):
        """Retrieve 40-column monospace printable driver transfer waybill / manifest."""
        transfer = self.get_object()
        raw_slip = transfer.format_waybill_thermal()

        fmt = (request.query_params.get('receipt_format') or request.query_params.get('format_type') or '').lower()
        if fmt in ['text', 'thermal'] or 'text/plain' in request.headers.get('Accept', ''):
            return HttpResponse(raw_slip, content_type='text/plain; charset=utf-8')

        return custome_success_response(
            message="Transfer waybill generated successfully.",
            data={
                "transfer_number": transfer.transfer_number,
                "source_store": transfer.source_store.name,
                "destination_store": transfer.destination_store.name,
                "status": transfer.status,
                "waybill_slip": raw_slip
            }
        )
