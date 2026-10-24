"""
Shared Enums — Common enumerations used across the project.
Use Django's TextChoices for database-backed fields.
"""
from django.db import models


class UserRoleEnum(models.TextChoices):
    """User roles across the platform."""
    SUPERUSER = "superuser", "Super User"
    STAFF     = "staff",     "Staff"
    VENDOR    = "vendor",    "Vendor"
    CUSTOMER  = "customer",  "Customer"
    USER      = "user",      "Regular User"


class StatusEnum(models.TextChoices):
    """Generic active/inactive status."""
    ACTIVE   = "active",   "Active"
    INACTIVE = "inactive", "Inactive"
    PENDING  = "pending",  "Pending"
    ARCHIVED = "archived", "Archived"


class SocialProviderEnum(models.TextChoices):
    """Supported social auth providers."""
    GOOGLE   = "google",   "Google"
    GITHUB   = "github",   "GitHub"
    FACEBOOK = "facebook", "Facebook"
    TWITTER  = "twitter",  "Twitter"
    LINKEDIN = "linkedin", "LinkedIn"
    APPLE    = "apple",    "Apple"


class PaymentStatusEnum(models.TextChoices):
    """Payment transaction statuses."""
    PENDING   = "pending",   "Pending"
    COMPLETED = "completed", "Completed"
    FAILED    = "failed",    "Failed"
    REFUNDED  = "refunded",  "Refunded"
    CANCELLED = "cancelled", "Cancelled"


class NotificationTypeEnum(models.TextChoices):
    """Types of system notifications."""
    WELCOME          = "welcome",          "Welcome"
    PASSWORD_CHANGED = "password_changed", "Password Changed"
    OTP              = "otp",              "OTP"
    SYSTEM           = "system",           "System"
    ALERT            = "alert",            "Alert"


class LogLevelEnum(models.TextChoices):
    """Log severity levels."""
    DEBUG    = "debug",    "Debug"
    INFO     = "info",     "Info"
    WARNING  = "warning",  "Warning"
    ERROR    = "error",    "Error"
    CRITICAL = "critical", "Critical"
