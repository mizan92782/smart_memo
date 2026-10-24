import pytz
from rest_framework_simplejwt.authentication import JWTAuthentication


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz_name = request.headers.get('X-Timezone')
        if tz_name:
            try:
                pytz.timezone(tz_name)  # validate
                try:
                    result = JWTAuthentication().authenticate(request)
                    if result:
                        user, _ = result
                        profile = getattr(user, 'profile', None)
                        if profile and profile.timezone != tz_name:
                            profile.timezone = tz_name
                            profile.save(update_fields=['timezone'])
                except Exception:
                    pass
            except pytz.UnknownTimeZoneError:
                pass
        return self.get_response(request)
