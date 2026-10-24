from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from inventory.models.reconciliation_mod import StockReconciliation
from inventory.serializers.reconciliation_ser import (
    StockReconciliationSerializer,
    StockReconciliationCreateSerializer
)
from inventory.services.reconciliation_service import ReconciliationService
from stores.models.store_mod import Store
from shared.permissions.permissions import IsVendor
from shared.responses.responses import custome_success_response, custome_error_response


class StockReconciliationViewSet(viewsets.ModelViewSet):
    """
    Physical Inventory Audit & Batch Stock Reconciliation ViewSet.
    Enforces strict vendor tenant isolation across physical count sessions.
    """
    serializer_class = StockReconciliationSerializer
    permission_classes = [IsAuthenticated, IsVendor]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            qs = StockReconciliation.objects.all()
        else:
            qs = StockReconciliation.objects.filter(store__vendor=user)

        store_id = self.request.query_params.get('store_id')
        if store_id:
            qs = qs.filter(store_id=store_id)

        return qs.select_related('store', 'initiated_by', 'applied_by').prefetch_related('items__product')

    def create(self, request, *args, **kwargs):
        serializer = StockReconciliationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        store_id = serializer.validated_data['store_id']
        store = Store.objects.filter(id=store_id).first()
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        if store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own this store.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            reconciliation = ReconciliationService.create_reconciliation(
                store=store,
                actor=request.user,
                items_data=serializer.validated_data['items'],
                notes=serializer.validated_data.get('notes', '')
            )
            return custome_success_response(
                message="Stock reconciliation draft created successfully.",
                data=StockReconciliationSerializer(reconciliation).data,
                status_code=status.HTTP_201_CREATED
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return custome_success_response(
            message="Stock reconciliation retrieved successfully.",
            data=serializer.data
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return custome_success_response(
            message="Stock reconciliations retrieved successfully.",
            data=serializer.data
        )

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Atomically post reconciliation count variances to inventory ledger balances."""
        instance = self.get_object()
        try:
            reconciliation = ReconciliationService.apply_reconciliation(
                reconciliation_id=instance.id,
                actor=request.user
            )
            return custome_success_response(
                message="Stock reconciliation applied successfully to ledger.",
                data=StockReconciliationSerializer(reconciliation).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a draft reconciliation session without modifying stock."""
        instance = self.get_object()
        try:
            reconciliation = ReconciliationService.cancel_reconciliation(
                reconciliation_id=instance.id,
                actor=request.user
            )
            return custome_success_response(
                message="Stock reconciliation draft cancelled.",
                data=StockReconciliationSerializer(reconciliation).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
