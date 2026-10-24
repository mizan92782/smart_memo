"""
Shared Responses — Standardized API response structure for the entire project.

All views must use these helpers for consistent JSON responses.
Response format:
    {
        "success": true/false,
        "message": "...",
        "data": {...} or null,
        "errors": null or {...}
    }
"""
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import exception_handler


# ─── Success Response ─────────────────────────────────────────────────────────

def custome_success_response(
    message: str = "Success",
    data=None,
    data_title: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    """
    Standard success response.

    Args:
        message: Human-readable success message.
        data: Response payload. Can be dict, list, or scalar.
        data_title: Optional key to wrap data under (e.g., data_title="user" → {"user": data}).
        status_code: HTTP status code (default 200).
    """
    payload = {
        "success": True,
        "message": message,
        "errors": None,
    }
    if data_title and data is not None:
        payload["data"] = {data_title: data}
    else:
        payload["data"] = data

    return Response(payload, status=status_code)


# ─── Error Response ───────────────────────────────────────────────────────────

def custome_error_response(
    message: str = "An error occurred",
    errors=None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    """
    Standard error response.

    Args:
        message: Human-readable error message.
        errors: Optional structured error details (dict or list).
        status_code: HTTP status code (default 400).
    """
    return Response(
        {
            "success": False,
            "message": message,
            "data": None,
            "errors": errors,
        },
        status=status_code,
    )


# ─── Global Exception Handler ──────────────────────────────────────────────────

def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler.
    Returns structured error responses for all exceptions.
    Set in REST_FRAMEWORK['EXCEPTION_HANDLER'] in settings.py.
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_data = response.data

        # Flatten DRF ValidationError detail
        if isinstance(error_data, dict):
            errors = {}
            for key, value in error_data.items():
                if isinstance(value, list):
                    errors[key] = value[0] if len(value) == 1 else value
                else:
                    errors[key] = value
            message = errors.pop('detail', 'Validation error')
            if isinstance(message, list):
                message = message[0]
        elif isinstance(error_data, list):
            errors = error_data
            message = "Validation error"
        else:
            errors = None
            message = str(error_data) if error_data else "An error occurred"

        response.data = {
            "success": False,
            "message": str(message),
            "data": None,
            "errors": errors if errors else None,
        }

    return response
