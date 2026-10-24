"""
users/signals.py — Django Signals for Users
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models.user_mod import User
from users.models.profile_mod import Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create a profile when a new user is created."""
    if created:
        Profile.objects.get_or_create(user=instance)
