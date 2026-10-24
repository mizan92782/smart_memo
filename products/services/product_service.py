"""
products/services/product_service.py — Business Logic for Products

Senior Pattern: Services encapsulate domain logic using static methods.
Views and APIs delegate business logic here.
"""
from decimal import Decimal
from typing import List
from products.models.product_mod import Product
from products.repositories.product_repository import ProductRepository


class ProductService:
    """Encapsulates business operations for Products."""

    @staticmethod
    def calculate_offered_price(price: Decimal, discount_percent: Decimal) -> Decimal:
        """Calculate final price after applying discount percentage."""
        if not discount_percent or discount_percent <= 0:
            return price
        discount_amount = price * (discount_percent / Decimal('100.0'))
        return round(price - discount_amount, 2)

    @staticmethod
    def build_product_tags(name: str, second_name: str, category_name: str) -> List[str]:
        """Generate search tags for a product."""
        tags = []
        if name:
            tags.append(name.strip().title())
        if second_name:
            tags.append(second_name.strip().title())
        if category_name:
            tags.append(category_name.strip().title())
        return list(dict.fromkeys(tags))[:5]  # unique, up to 5

    @staticmethod
    def check_stock_availability(product: Product, requested_quantity: Decimal) -> bool:
        """Check if enough inventory exists for requested quantity."""
        return product.stock >= requested_quantity

    @staticmethod
    def apply_discount(product: Product, discount_percent: Decimal) -> Product:
        """Apply a promotional discount to a product."""
        product.offer = True
        product.offered_discount = discount_percent
        product.offered_price = ProductService.calculate_offered_price(product.price, discount_percent)
        product.save()
        return product
