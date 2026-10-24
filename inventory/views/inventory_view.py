from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry
from inventory.serializers.inventory_ser import (
    StockBalanceSerializer,
    StockLedgerEntrySerializer,
    StockAdjustmentSerializer
)
from inventory.repositories.inventory_repository import InventoryRepository
from inventory.services.inventory_service import InventoryService
from products.models.product_mod import Product
from stores.models.store_mod import Store
from shared.permissions.permissions import IsVendor
from shared.responses.responses import custome_success_response, custome_error_response


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet to inspect stock balances and execute inventory adjustments."""
    serializer_class = StockBalanceSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        vendor_stores = self.request.user.stores.values_list('id', flat=True)
        store_id = self.request.query_params.get('store_id')
        if store_id:
            return StockBalance.objects.filter(store_id=int(store_id), store__vendor=self.request.user)
        return StockBalance.objects.filter(store_id__in=vendor_stores)

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Returns products with available stock at or below low stock threshold."""
        balances = [b for b in self.get_queryset() if b.is_low_stock]
        serializer = self.get_serializer(balances, many=True)
        return custome_success_response(
            message="Low stock balances retrieved.",
            data=serializer.data
        )

    @action(detail=False, methods=['post'])
    def adjust(self, request):
        """Execute a manual stock adjustment, damage write-off, or return."""
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        reason = serializer.validated_data.get('reason', 'manual_adjustment')
        notes = serializer.validated_data.get('notes', '')

        product = Product.objects.filter(pk=product_id, is_deleted=False).select_related('store').first()
        if not product or not product.store:
            return custome_error_response("Product or store not found.", status_code=status.HTTP_404_NOT_FOUND)

        if product.store.vendor != request.user and not request.user.is_superuser:
            return custome_error_response("You do not own the store for this product.", status_code=status.HTTP_403_FORBIDDEN)

        try:
            balance = InventoryService.adjust_stock(
                store=product.store,
                product=product,
                quantity=quantity,
                movement_type=reason,
                actor=request.user,
                notes=notes
            )
            return custome_success_response(
                message="Stock adjusted successfully.",
                data=StockBalanceSerializer(balance).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)


class StockLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only audit ledger of all stock movements for the vendor's stores."""
    serializer_class = StockLedgerEntrySerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        vendor_stores = self.request.user.stores.values_list('id', flat=True)
        store_id = self.request.query_params.get('store_id')
        if store_id:
            return StockLedgerEntry.objects.filter(store_id=int(store_id), store__vendor=self.request.user).order_by('-created_at')
        return StockLedgerEntry.objects.filter(store_id__in=vendor_stores).order_by('-created_at')
