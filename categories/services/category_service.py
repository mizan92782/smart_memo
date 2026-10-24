"""
categories/services/category_service.py — Business Logic for Categories

Senior Pattern: Encapsulates domain logic using static methods.
"""
from categories.models.category_mod import Category
from categories.repositories.category_repository import CategoryRepository


class CategoryService:
    """Encapsulates business operations for Category."""

    @staticmethod
    def get_or_create_category(name: str) -> Category:
        """Get an existing category or create a new one."""
        cleaned_name = name.strip().title()
        category = CategoryRepository.get_by_name(cleaned_name)
        if not category:
            category = CategoryRepository.create_category(cleaned_name)
        return category

    @staticmethod
    def get_category_product_counts() -> list:
        """Return category list with product counts."""
        categories = CategoryRepository.get_all_with_products()
        return [
            {
                "id": c.id,
                "name": c.name,
                "product_count": c.products.count()
            }
            for c in categories
        ]
