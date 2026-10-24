from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views.user_view import UserViewSet
from users.views.address_view import CustomerAddressViewSet

router = DefaultRouter()
router.register(r'addresses', CustomerAddressViewSet, basename='customer-address')
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]
