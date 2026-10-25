from django.urls import path, include
from rest_framework.routers import DefaultRouter
from orders.views.order_view import OrderViewSet
from orders.views.return_view import OrderReturnViewSet

router = DefaultRouter()
router.register(r'returns', OrderReturnViewSet, basename='order-return')
router.register(r'', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
]

