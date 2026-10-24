"""
Shared Throttling — Custom throttle classes for project-wide rate limiting.

Usage: Set throttle_classes = [LoginUserThrottle, LoginAnonThrottle] on views.
Rates are also configured in settings.py under REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].
"""
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

FIVE_MINUTES = 5 * 60  # 300 seconds


# ─── Login Throttles ──────────────────────────────────────────────────────────

class LoginUserThrottle(UserRateThrottle):
    """5 login attempts per 5 minutes for authenticated users."""
    scope = 'login_user'

    def parse_rate(self, rate):
        return (5, FIVE_MINUTES)


class LoginAnonThrottle(AnonRateThrottle):
    """5 login attempts per 5 minutes for anonymous users."""
    scope = 'login_anon'

    def parse_rate(self, rate):
        return (5, FIVE_MINUTES)


# ─── Signup Throttles ─────────────────────────────────────────────────────────

class SignupUserThrottle(UserRateThrottle):
    """5 signup attempts per 5 minutes for authenticated users."""
    scope = 'signup_user'

    def parse_rate(self, rate):
        return (5, FIVE_MINUTES)


class SignupAnonThrottle(AnonRateThrottle):
    """5 signup attempts per 5 minutes for anonymous users."""
    scope = 'signup_anon'

    def parse_rate(self, rate):
        return (5, FIVE_MINUTES)


# ─── OTP Throttles ────────────────────────────────────────────────────────────

class OTPThrottle(AnonRateThrottle):
    """10 OTP requests per hour. Prevents OTP spam."""
    scope = 'otp'
    rate = '10/hour'


# ─── Password Reset Throttles ─────────────────────────────────────────────────

class PasswordResetThrottle(AnonRateThrottle):
    """5 password reset attempts per hour. Prevents abuse."""
    scope = 'password_reset'
    rate = '5/hour'


# ─── Social Auth Throttles ────────────────────────────────────────────────────

class SocialAuthThrottle(AnonRateThrottle):
    """10 social auth attempts per hour. Prevents OAuth spam."""
    scope = 'social_auth'
    rate = '10/hour'


# ─── API Burst Throttle ───────────────────────────────────────────────────────

class BurstRateThrottle(AnonRateThrottle):
    """
    General burst throttle: 60 requests per minute.
    Apply to any high-frequency public endpoint.
    """
    scope = 'burst'
    rate = '60/min'


class SustainedRateThrottle(UserRateThrottle):
    """
    General sustained throttle: 1000 requests per hour for authenticated users.
    """
    scope = 'sustained'
    rate = '1000/hour'
