"""
cards/validators/card_validator.py — Custom Validators for Card
"""
from decimal import Decimal
from django.core.exceptions import ValidationError


def validate_card_item_quantity(quantity: Decimal) -> None:
    """Validate quantity is greater than 0."""
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")
