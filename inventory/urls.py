from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventory.views.inventory_view import InventoryViewSet, StockLedgerViewSet
from inventory.views.reconciliation_view import StockReconciliationViewSet
from inventory.views.transfer_view import StockTransferViewSet

router = DefaultRouter()
router.register(r'balances', InventoryViewSet, basename='inventory-balance')
router.register(r'ledger', StockLedgerViewSet, basename='inventory-ledger')
router.register(r'reconciliations', StockReconciliationViewSet, basename='inventory-reconciliation')
router.register(r'transfers', StockTransferViewSet, basename='inventory-transfer')

urlpatterns = [
    path('', include(router.urls)),
]

