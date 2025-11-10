from django.urls import path
from products import views
urlpatterns=[
    path('product_list', views.ProductList.as_view(), name='product-list'),
    path('category_product_list/<int:pk>/', views.Category_Products_ListView.as_view(), name='category_products'),
]