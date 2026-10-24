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
