from rest_framework.routers import DefaultRouter
from purchases.views.purchase_view import SupplierViewSet, PurchaseViewSet

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'orders', PurchaseViewSet, basename='purchase')

urlpatterns = router.urls
