from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from stores.models.store_mod import Store
from reports.serializers.report_ser import DateRangeFilterSerializer, StoreFilterSerializer
from reports.services.report_service import ReportService
from shared.permissions.permissions import IsVendor
from shared.responses.responses import custome_success_response, custome_error_response


class ReportViewSet(viewsets.ViewSet):
    """
    Vendor analytics and reports endpoint.
    Aggregates sales performance, inventory health, and purchase volumes
    with strict store ownership verification.
    """
    permission_classes = [IsAuthenticated, IsVendor]

    def _get_authorized_store(self, request, store_id: int):
        store = Store.objects.filter(pk=store_id, is_deleted=False).first()
        if not store:
            return None, custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        if store.vendor != request.user and not request.user.is_superuser:
            return None, custome_error_response(
                "You do not own this store.",
                status_code=status.HTTP_403_FORBIDDEN
            )
        return store, None

    @action(detail=False, methods=['get'], url_path='vendor-summary')
    def vendor_summary(self, request):
        """Unified dashboard report endpoint for vendor store view."""
        store_id = request.query_params.get('store_id')
        if not store_id:
            return custome_error_response("store_id query param is required.", status_code=status.HTTP_400_BAD_REQUEST)

        store, err = self._get_authorized_store(request, int(store_id))
        if err:
            return err

        sales_data = ReportService.get_sales_report(store=store)
        inv_data = ReportService.get_inventory_report(store=store)
        hot_products = ReportService.get_hot_products(store=store)

        financials = sales_data.get('financials', {})
        orders_info = sales_data.get('orders', {})

        data = {
            "store_id": store.id,
            "store_name": store.name,
            "gross_sales": financials.get('gross_sales', '0.00'),
            "net_product_sales": financials.get('net_product_sales', '0.00'),
            "delivery_fees_collected": financials.get('delivery_fees_collected', '0.00'),
            "cod_collected": financials.get('cod_collected', '0.00'),
            "cod_outstanding": financials.get('cod_outstanding', '0.00'),
            "total_orders": orders_info.get('total', 0),
            "completed_orders": orders_info.get('completed', 0),
            "cancelled_orders": orders_info.get('cancelled', 0),
            "total_tracked_products": inv_data.get('total_tracked_products', 0),
            "low_stock_items": inv_data.get('low_stock_items', []),
            "hot_products": hot_products,
        }
        return custome_success_response(data=data)

    @action(detail=False, methods=['get'])
    def sales(self, request):
        """Sales performance report."""
        serializer = DateRangeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        store_id = serializer.validated_data['store_id']
        store, err = self._get_authorized_store(request, store_id)
        if err:
            return err

        data = ReportService.get_sales_report(
            store=store,
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date')
        )
        return custome_success_response(data=data)

    @action(detail=False, methods=['get'])
    def inventory(self, request):
        """Inventory status and low-stock alert report."""
        serializer = StoreFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        store_id = serializer.validated_data['store_id']
        store, err = self._get_authorized_store(request, store_id)
        if err:
            return err

        data = ReportService.get_inventory_report(store=store)
        return custome_success_response(data=data)

    @action(detail=False, methods=['get'])
    def purchases(self, request):
        """Procurement and purchase volume report."""
        serializer = DateRangeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        store_id = serializer.validated_data['store_id']
        store, err = self._get_authorized_store(request, store_id)
        if err:
            return err

        data = ReportService.get_purchases_report(
            store=store,
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date')
        )
        return custome_success_response(data=data)

    @action(detail=False, methods=['get'], url_path='export-sales-tax')
    def export_sales_tax(self, request):
        """Download accounting and sales tax report as UTF-8 CSV."""
        from reports.services.export_service import ExportService
        serializer = DateRangeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        store_id = serializer.validated_data['store_id']
        store, err = self._get_authorized_store(request, store_id)
        if err:
            return err

        return ExportService.export_sales_tax_csv(
            store=store,
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date')
        )

    @action(detail=False, methods=['get'], url_path='export-inventory-valuation')
    def export_inventory_valuation(self, request):
        """Download inventory valuation and stock levels as UTF-8 CSV."""
        from reports.services.export_service import ExportService
        serializer = StoreFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        store_id = serializer.validated_data['store_id']
        store, err = self._get_authorized_store(request, store_id)
        if err:
            return err

        return ExportService.export_inventory_valuation_csv(store=store)

    @action(detail=False, methods=['get'], url_path='export-purchases')
    def export_purchases(self, request):
        """Download procurement history and supplier accounts payable as UTF-8 CSV."""
        from reports.services.export_service import ExportService
        serializer = DateRangeFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        store_id = serializer.validated_data['store_id']
        store, err = self._get_authorized_store(request, store_id)
        if err:
            return err

        return ExportService.export_purchases_procurement_csv(
            store=store,
            start_date=serializer.validated_data.get('start_date'),
            end_date=serializer.validated_data.get('end_date')
        )

    @action(detail=False, methods=['get'], url_path='export-batches')
    def export_batches(self, request):
        """Download perishable batch expiry, clearance status, and valuation as UTF-8 CSV."""
        from reports.services.export_service import ExportService
        serializer = StoreFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        store_id = serializer.validated_data['store_id']
        store, err = self._get_authorized_store(request, store_id)
        if err:
            return err

        return ExportService.export_perishable_batches_csv(store=store)
