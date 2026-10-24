"""
middleware/request_log_middleware.py — Request Logging Middleware

Logs every API request with:
  - HTTP method
  - API path
  - HTTP status code
  - Authenticated user ID (or "anonymous")
  - Request duration (ms)
  - Timestamp

Uses the colored formatter from logs/ for terminal output.
"""
import logging
import time

logger = logging.getLogger('api.requests')


class RequestLogMiddleware:
    """
    Django WSGI middleware that logs all incoming HTTP requests.

    Install in settings.py MIDDLEWARE (after SecurityMiddleware):
        'middleware.request_log_middleware.RequestLogMiddleware',
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ── Before view ──────────────────────────────────────────────────────
        start_time = time.time()

        # Process the request through the view
        response = self.get_response(request)

        # ── After view ───────────────────────────────────────────────────────
        duration_ms = (time.time() - start_time) * 1000

        # Resolve user identity
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            user_id = str(user.id)
        else:
            user_id = 'anonymous'

        status_code = response.status_code
        api_path = request.get_full_path()
        method = request.method

        # Select log level based on status code
        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # Emit the log record with extra metadata for the formatter
        logger.log(
            log_level,
            f"{method} {api_path}",
            extra={
                'status_code':  status_code,
                'api_path':     api_path,
                'user_id':      user_id,
                'method':       method,
                'duration_ms':  round(duration_ms, 2),
            }
        )

        return response
