"""
Shared Constants — Project-wide constants used across all apps.
Import from here rather than defining constants in individual apps.
"""

# ─── App Identity ────────────────────────────────────────────────────────────
APP_NAME = "IKON"
COMPANY_NAME = "IKON"

# ─── Cache Key Prefixes ───────────────────────────────────────────────────────
CACHE_PREFIX_REGISTER       = "register"
CACHE_PREFIX_PASSWORD_RESET = "password_reset"
CACHE_PREFIX_EMAIL_VERIFY   = "email_verify"
CACHE_PREFIX_OTP_COOLDOWN   = "otp_cooldown"
CACHE_PREFIX_TOKEN_BLACKLIST = "blacklist"
CACHE_PREFIX_PRODUCT        = "product"
CACHE_PREFIX_CATEGORY       = "category"
CACHE_PREFIX_SESSION        = "session"

# ─── OTP Settings ─────────────────────────────────────────────────────────────
OTP_LENGTH          = 6
OTP_EXPIRY_SECONDS  = 300    # 5 minutes
OTP_COOLDOWN_SECONDS = 60   # 1 minute between resends

# ─── Token Settings ───────────────────────────────────────────────────────────
ACCESS_TOKEN_LIFETIME_DAYS  = 60
REFRESH_TOKEN_LIFETIME_DAYS = 60
PASSWORD_RESET_TOKEN_EXPIRY = 300  # 5 minutes

# ─── Pagination ───────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE     = 100

# ─── File Uploads ─────────────────────────────────────────────────────────────
MAX_IMAGE_SIZE_MB  = 5
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']

# ─── Rate Limiting ────────────────────────────────────────────────────────────
THROTTLE_RATE_LOGIN           = "5/min"
THROTTLE_RATE_SIGNUP          = "5/min"
THROTTLE_RATE_OTP             = "10/hour"
THROTTLE_RATE_PASSWORD_RESET  = "5/hour"
THROTTLE_RATE_SOCIAL_AUTH     = "10/hour"

# ─── HTTP Status Messages ─────────────────────────────────────────────────────
MSG_SUCCESS              = "Success"
MSG_CREATED              = "Created successfully"
MSG_UPDATED              = "Updated successfully"
MSG_DELETED              = "Deleted successfully"
MSG_NOT_FOUND            = "Resource not found"
MSG_UNAUTHORIZED         = "Authentication credentials were not provided"
MSG_FORBIDDEN            = "You do not have permission to perform this action"
MSG_VALIDATION_ERROR     = "Validation error"
MSG_SERVER_ERROR         = "An internal server error occurred"

# ─── Social Auth Providers ───────────────────────────────────────────────────
SOCIAL_PROVIDER_GOOGLE   = "google"
SOCIAL_PROVIDER_GITHUB   = "github"
SOCIAL_PROVIDER_FACEBOOK = "facebook"
SOCIAL_PROVIDER_TWITTER  = "twitter"
SOCIAL_PROVIDER_LINKEDIN = "linkedin"
SOCIAL_PROVIDER_APPLE    = "apple"
