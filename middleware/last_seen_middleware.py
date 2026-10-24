"""
middleware/last_seen_middleware.py — Last Seen Middleware

Updates the authenticated user's UserProfile.last_seen timestamp
on every authenticated request. Used for showing user activity.
"""
from django.utils import timezone


class LastSeenMiddleware:
    """
    Updates UserProfile.last_seen for every authenticated request.

    Install in settings.py MIDDLEWARE:
        'middleware.last_seen_middleware.LastSeenMiddleware',
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only update for authenticated users
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            self._update_last_seen(user)

        return response

    @staticmethod
    def _update_last_seen(user) -> None:
        """Update the user's last_seen timestamp. Silently ignores errors."""
        try:
            from authentication.models.profile_mod import UserProfile
            UserProfile.objects.filter(user=user).update(last_seen=timezone.now())
        except Exception:
            pass
