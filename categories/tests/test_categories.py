"""
categories/tests/test_categories.py — Tests for Category Model and Views
"""
from django.test import TestCase
from categories.models.category_mod import Category
from categories.repositories.category_repository import CategoryRepository


class CategoryModelTests(TestCase):
    def test_create_category(self):
        category = CategoryRepository.create_category("fruits")
        self.assertEqual(category.name, "Fruits")
        self.assertEqual(str(category), "Fruits")
