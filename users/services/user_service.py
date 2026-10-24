"""
users/services/user_service.py — Business Logic for User Management
"""
from typing import Optional, Tuple
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
        profile, _ = Profile.objects.get_or_create(user=user, defaults={'full_name': full_name})
        return user, profile

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str) -> bool:
        """Change user password after verifying current password."""
        if not user.check_password(current_password):
            return False
        UserRepository.set_password(user, new_password)
        return True

    @staticmethod
    def update_profile(user: User, **profile_data) -> Profile:
        """Update profile details for a user."""
        profile, _ = Profile.objects.get_or_create(user=user)
        for key, value in profile_data.items():
            setattr(profile, key, value)
        profile.save()
        return profile
