from django.urls import path, include
from rest_framework.routers import DefaultRouter
from products.views.product_view import ProductList, Category_Products_ListView, ProductViewSet

router = DefaultRouter()
router.register(r'api', ProductViewSet, basename='product-api')

urlpatterns = [
    path('product_list', ProductList.as_view(), name='product-list'),
    path('category_product_list/<int:pk>/', Category_Products_ListView.as_view(), name='category_products'),
    path('', include(router.urls)),
]