from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventory.views.inventory_view import InventoryViewSet, StockLedgerViewSet

router = DefaultRouter()
router.register(r'balances', InventoryViewSet, basename='inventory-balance')
router.register(r'ledger', StockLedgerViewSet, basename='inventory-ledger')

urlpatterns = [
    path('', include(router.urls)),
]
