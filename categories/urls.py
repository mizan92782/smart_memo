from django.urls import path, include
from rest_framework.routers import DefaultRouter
from categories.views.category_view import CategoryViewSet

router = DefaultRouter()
router.register(r'api', CategoryViewSet, basename='category-api')
router.register(r'', CategoryViewSet, basename='category')

urlpatterns = [
    path('', include(router.urls)),
]