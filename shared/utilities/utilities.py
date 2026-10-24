"""
Shared Utilities — Common utility functions used across the project.
"""
import uuid
import hashlib
import random
import json
from datetime import datetime
from typing import Any
from django.utils import timezone


# ─── OTP Utilities ────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP of the given length."""
    lower = 10 ** (length - 1)
    upper = 10 ** length - 1
    return str(random.randint(lower, upper))


def hash_otp(otp: str) -> str:
    """Hash an OTP using SHA-256 for secure storage."""
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """Verify a plain OTP against its hash."""
    return hash_otp(plain_otp) == hashed_otp


# ─── Token Utilities ──────────────────────────────────────────────────────────

def generate_reset_token() -> str:
    """Generate a secure UUID token for password reset."""
    return str(uuid.uuid4())


# ─── Image Path Utilities ─────────────────────────────────────────────────────

def profile_image_path(instance, filename: str) -> str:
    """Generate a unique upload path for profile images."""
    ext = filename.split('.')[-1]
    return f"profile_dp/{uuid.uuid4()}.{ext}"


def generic_upload_path(folder: str):
    """Factory that generates an upload_to function for any folder."""
    def _path(instance, filename: str) -> str:
        ext = filename.split('.')[-1]
        return f"{folder}/{uuid.uuid4()}.{ext}"
    return _path


# ─── Date/Time Utilities ──────────────────────────────────────────────────────

def now_aware() -> datetime:
    """Return the current datetime with timezone awareness."""
    return timezone.now()


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format a datetime object to a string."""
    if dt is None:
        return ""
    return dt.strftime(fmt)


# ─── Data Utilities ───────────────────────────────────────────────────────────

def safe_json_loads(value: str | None) -> Any:
    """Safely parse a JSON string. Returns None on failure."""
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def safe_json_dumps(value: Any) -> str:
    """Safely serialize a value to JSON string."""
    return json.dumps(value, default=str)


def flatten_errors(errors: dict) -> dict:
    """
    Flatten nested DRF error dicts to single-level key → message.
    {'field': ['Error message']} → {'field': 'Error message'}
    """
    flat = {}
    for key, value in errors.items():
        if isinstance(value, list) and len(value) == 1:
            flat[key] = str(value[0])
        elif isinstance(value, list):
            flat[key] = [str(v) for v in value]
        else:
            flat[key] = str(value)
    return flat


# ─── String Utilities ─────────────────────────────────────────────────────────

def get_client_ip(request) -> str:
    """Extract the real client IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def mask_email(email: str) -> str:
    """
    Mask an email address for display (e.g., j***@example.com).
    """
    try:
        local, domain = email.split('@')
        masked_local = local[0] + '***' if len(local) > 1 else '***'
        return f"{masked_local}@{domain}"
    except Exception:
        return "***"
