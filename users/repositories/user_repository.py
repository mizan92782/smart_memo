"""
users/repositories/user_repository.py — Database Query Logic for User

Senior Pattern: Repositories are NOT instantiated (static methods only).
Single source of truth for User DB interactions.
"""
from typing import Optional
from django.contrib.auth import authenticate
from django.db.models import QuerySet
from users.models.user_mod import User


class UserRepository:
    """Handles all database operations for the User model."""

    @staticmethod
    def get_by_email(email: str) -> Optional[User]:
        """Fetch user by email."""
        return User.objects.filter(email__iexact=email).first()

    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        """Fetch user by ID."""
        return User.objects.filter(pk=user_id).first()

    @staticmethod
    def exists_by_email(email: str) -> bool:
        """Check if user exists with email."""
        return User.objects.filter(email__iexact=email).exists()

    @staticmethod
    def create_user(email: str, password: str = None, **extra_fields) -> User:
        """Create a new user."""
        return User.objects.create_user(email=email, password=password, **extra_fields)

    @staticmethod
    def authenticate(email: str, password: str) -> Optional[User]:
        """Authenticate user against credentials."""
        return authenticate(email=email, password=password)

    @staticmethod
    def set_password(user: User, new_password: str) -> None:
        """Update user password."""
        user.set_password(new_password)
        user.save(update_fields=['password'])

    @staticmethod
    def list_users() -> QuerySet[User]:
        """List all active users."""
        return User.objects.filter(is_active=True).select_related('profile')

    @staticmethod
    def delete_user(user: User) -> None:
        """Delete user account."""
        user.delete()
