"""
users/validators/user_validator.py — Custom Validators for User
"""
from django.core.exceptions import ValidationError


def validate_password_strength(password: str) -> None:
    """Validate that password meets security requirements."""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not any(char.isdigit() for char in password):
        raise ValidationError("Password must contain at least one digit.")
