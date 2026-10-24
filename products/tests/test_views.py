"""
products/tests/test_views.py — Tests for Product Views
"""
from django.test import TestCase
from django.urls import reverse
from categories.models.category_mod import Category
from products.models.product_mod import Product


class ProductViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Groceries")
        self.product = Product.objects.create(
            name="Apple",
            category=self.category,
            price=120.00,
            stock=10
        )

    def test_product_list_view(self):
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apple")

    def test_category_products_view(self):
        url = reverse('category_products', kwargs={'pk': self.category.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apple")
