from django.urls import path, include
from rest_framework.routers import DefaultRouter
from stores.views.store_view import StoreViewSet

router = DefaultRouter()
router.register(r'', StoreViewSet, basename='store')

urlpatterns = [
    path('', include(router.urls)),
]
