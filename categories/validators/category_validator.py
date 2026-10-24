"""
categories/validators/category_validator.py — Custom Validators for Categories
"""
from django.core.exceptions import ValidationError


def validate_category_name(value: str) -> None:
    """Validate that category name is not empty and has valid length."""
    if not value or not value.strip():
        raise ValidationError("Category name cannot be empty.")
    if len(value.strip()) < 2:
        raise ValidationError("Category name must have at least 2 characters.")
