from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from purchases.models.purchase_mod import Supplier, Purchase, PurchaseStatus
from purchases.serializers.purchase_ser import (
    SupplierSerializer,
    PurchaseSerializer,
    PurchaseCreateSerializer,
    GenerateLowStockPOSerializer,
)
from purchases.services.purchase_service import PurchaseService
from stores.models.store_mod import Store
from shared.permissions.permissions import IsVendor
from shared.responses.responses import custome_success_response, custome_error_response


class SupplierViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for store-scoped suppliers.
    Only authorized vendors can manage suppliers for their owned stores.
    """
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        user = self.request.user
        qs = Supplier.objects.filter(is_deleted=False)
        if not user.is_superuser:
            qs = qs.filter(store__vendor=user)

        store_id = self.request.query_params.get('store_id')
        if store_id:
            qs = qs.filter(store_id=store_id)
        return qs.order_by('name')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        store = serializer.validated_data['store']
        if store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response(
                "You do not own this store.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        supplier = serializer.save()
        return custome_success_response(
            message="Supplier created successfully.",
            data=SupplierSerializer(supplier).data,
            status_code=status.HTTP_201_CREATED
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return custome_success_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return custome_success_response(data=serializer.data)


class PurchaseViewSet(viewsets.ModelViewSet):
    """
    Purchase Order management: draft, submit, receive goods into stock, or cancel.
    Strictly isolated to vendor's store.
    """
    serializer_class = PurchaseSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        user = self.request.user
        qs = Purchase.objects.filter(is_deleted=False)
        if not user.is_superuser:
            qs = qs.filter(store__vendor=user)

        store_id = self.request.query_params.get('store_id')
        if store_id:
            qs = qs.filter(store_id=store_id)

        purchase_status = self.request.query_params.get('status')
        if purchase_status:
            qs = qs.filter(status=purchase_status)

        return (
            qs
            .select_related('store', 'supplier', 'created_by')
            .prefetch_related('items__product')
            .order_by('-created_at')
        )

    def create(self, request, *args, **kwargs):
        serializer = PurchaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        store_id = serializer.validated_data['store_id']
        supplier_id = serializer.validated_data['supplier_id']

        store = Store.objects.filter(pk=store_id, is_deleted=False).first()
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        if store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own this store.", status_code=status.HTTP_403_FORBIDDEN)

        supplier = Supplier.objects.filter(pk=supplier_id, store=store, is_deleted=False).first()
        if not supplier:
            return custome_error_response(
                "Supplier not found for this store.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        try:
            purchase = PurchaseService.create_purchase(
                store=store,
                supplier=supplier,
                items_data=serializer.validated_data['items'],
                reference=serializer.validated_data.get('reference', ''),
                additional_charges=serializer.validated_data.get('additional_charges', 0),
                notes=serializer.validated_data.get('notes', ''),
                actor=request.user
            )
            return custome_success_response(
                message="Purchase draft created successfully.",
                data=PurchaseSerializer(purchase).data,
                status_code=status.HTTP_201_CREATED
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return custome_success_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return custome_success_response(data=serializer.data)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit a draft purchase order."""
        purchase = self.get_object()
        try:
            purchase = PurchaseService.submit_purchase(purchase, actor=request.user)
            return custome_success_response(
                message="Purchase order submitted.",
                data=PurchaseSerializer(purchase).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """Confirm receipt of goods and increment inventory on-hand balance."""
        purchase = self.get_object()
        try:
            purchase = PurchaseService.receive_purchase(purchase.id, actor=request.user)
            return custome_success_response(
                message="Purchase goods received and added to inventory.",
                data=PurchaseSerializer(purchase).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a draft or submitted purchase order."""
        purchase = self.get_object()
        try:
            purchase = PurchaseService.cancel_purchase(purchase.id, actor=request.user)
            return custome_success_response(
                message="Purchase order cancelled.",
                data=PurchaseSerializer(purchase).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='generate-low-stock-pos')
    def generate_low_stock_pos(self, request):
        """
        Evaluate store low stock balances and automatically generate draft purchase orders.
        """
        serializer = GenerateLowStockPOSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        store_id = data['store_id']
        store = Store.objects.filter(pk=store_id).first()
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        if store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response(
                "You do not own this store.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        default_supplier = None
        default_supplier_id = data.get('default_supplier_id')
        if default_supplier_id:
            default_supplier = Supplier.objects.filter(pk=default_supplier_id, store=store, is_deleted=False).first()
            if not default_supplier:
                return custome_error_response(
                    "Default supplier not found for this store.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        try:
            report = PurchaseService.generate_low_stock_purchase_orders(
                store=store,
                default_supplier=default_supplier,
                include_open_order_guard=data.get('include_open_order_guard', True),
                actor=request.user
            )
            return custome_success_response(
                message=f"Generated {report['created_orders_count']} automated draft purchase order(s).",
                data=report,
                status_code=status.HTTP_201_CREATED if report['created_orders_count'] > 0 else status.HTTP_200_OK
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
