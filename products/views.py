from django.shortcuts import render
from django.views.generic import ListView

from .models import Product



class ProductList(ListView):
    model = Product
    context_object_name = 'products'
    template_name='products.html'
    ordering = ['name']


from .models import Category


class Category_Products_ListView(ListView):
    model = Category
    template_name = 'category_products.html'
    context_object_name = 'products'

    def get_queryset(self):
        return Product.objects.filter(category_id=self.kwargs['pk']).order_by('name')