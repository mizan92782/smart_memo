from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ObjectDoesNotExist

THROTTLE_SECONDS = 300  # update at most once every 5 minutes


class LastSeenMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated or user.is_staff:
            return response

        now = timezone.now()
        try:
            profile = user.profile
            if profile.last_seen is None or (now - profile.last_seen).total_seconds() >= THROTTLE_SECONDS:
                profile.last_seen = now
                profile.save(update_fields=['last_seen'])
        except ObjectDoesNotExist:
            pass

        return response
