"""
Shared Exceptions — Custom exception classes for project-wide use.
These exceptions are caught by the global exception handler in shared/responses/.
"""
from rest_framework import status
from rest_framework.exceptions import APIException


class ApplicationError(APIException):
    """
    Base exception for all custom application errors.
    Provides a structured error format consistent with the API response schema.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "An unexpected application error occurred."
    default_code = "application_error"


class NotFoundException(ApplicationError):
    """Raised when a requested resource is not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "not_found"


class ValidationException(ApplicationError):
    """Raised for business-rule validation failures (not field-level validation)."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Validation failed."
    default_code = "validation_error"


class AuthenticationException(ApplicationError):
    """Raised when authentication fails."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication credentials are invalid or expired."
    default_code = "authentication_error"


class PermissionDeniedException(ApplicationError):
    """Raised when a user does not have permission for an action."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"


class ConflictException(ApplicationError):
    """Raised when a resource conflict occurs (e.g., duplicate email)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A conflict occurred with an existing resource."
    default_code = "conflict"


class ServiceUnavailableException(ApplicationError):
    """Raised when an external service (email, Redis, etc.) is unavailable."""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "An external service is currently unavailable. Please try again later."
    default_code = "service_unavailable"


class OTPExpiredException(ValidationException):
    """Raised when an OTP has expired."""
    default_detail = "The OTP has expired. Please request a new one."
    default_code = "otp_expired"


class OTPInvalidException(ValidationException):
    """Raised when an OTP is incorrect."""
    default_detail = "The OTP you entered is incorrect."
    default_code = "otp_invalid"


class AccountInactiveException(AuthenticationException):
    """Raised when a user attempts to log in with a deactivated account."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "This account has been deactivated. Please contact support."
    default_code = "account_inactive"
