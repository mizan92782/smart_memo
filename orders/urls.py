from django.urls import path, include
from rest_framework.routers import DefaultRouter
from orders.views.order_view import OrderViewSet

router = DefaultRouter()
router.register(r'', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
]
