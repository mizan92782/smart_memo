"""
users/services/user_service.py — Business Logic for User Management
"""
from typing import Optional, Tuple
from django.contrib.auth import login as django_login, logout as django_logout
from rest_framework.exceptions import ValidationError, PermissionDenied
from users.models.user_mod import User
from users.models.profile_mod import Profile
from users.repositories.user_repository import UserRepository


class UserService:
    """Encapsulates business operations for User accounts."""

    @staticmethod
    def register_user(email: str, password: str, full_name: str = "", role: str = None) -> Tuple[User, Profile]:
        """Register a new user and initialize profile."""
        extra = {}
        if role:
            extra['role'] = role
        user = UserRepository.create_user(email=email, password=password, **extra)
        profile, _ = Profile.objects.get_or_create(user=user)
        if full_name:
            profile.full_name = full_name
            profile.save(update_fields=['full_name'])
        return user, profile

    @staticmethod
    def login_user(email: str, password: str, request=None) -> Tuple[User, str]:
        """
        Authenticate credentials and return user with active auth token.
        Raises ValidationError on bad credentials, PermissionDenied if account is inactive.
        """
        user = UserRepository.get_by_email(email)
        if not user or not user.check_password(password):
            raise ValidationError("Invalid email or password.")
        if not user.is_active:
            raise PermissionDenied("Account is disabled.")

        token = UserRepository.get_or_create_token(user)

        if request is not None:
            django_req = getattr(request, '_request', request)
            try:
                django_login(django_req, user)
            except Exception:
                pass

        return user, token.key


    @staticmethod
    def logout_user(user: User, request=None) -> None:
        """Invalidate active auth tokens and terminate session."""
        UserRepository.revoke_token(user)
        if request is not None:
            django_req = getattr(request, '_request', request)
            try:
                django_logout(django_req)
            except Exception:
                pass

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change user password after verifying current password.
        Rotates auth token to invalidate previous sessions.
        """
        if not user.check_password(current_password):
            raise ValidationError("Current password is incorrect.")
        UserRepository.set_password(user, new_password)
        new_token = UserRepository.rotate_token(user)
        return True, new_token.key

    @staticmethod
    def update_profile(user: User, **profile_data) -> Profile:
        """Update profile details for a user."""
        profile, _ = Profile.objects.get_or_create(user=user)
        for key, value in profile_data.items():
            setattr(profile, key, value)
        profile.save()
        return profile

