"""
products/validators/product_validator.py — Custom Validators for Products
"""
from decimal import Decimal
from django.core.exceptions import ValidationError


def validate_positive_price(value: Decimal) -> None:
    """Validate that price is greater than zero."""
    if value <= 0:
        raise ValidationError("Price must be greater than zero.")


def validate_discount_percentage(value: Decimal) -> None:
    """Validate that discount is between 0% and 100%."""
    if value < 0 or value > 100:
        raise ValidationError("Discount percentage must be between 0 and 100.")


def validate_stock_quantity(value: Decimal) -> None:
    """Validate that stock cannot be negative."""
    if value < 0:
        raise ValidationError("Stock quantity cannot be negative.")
