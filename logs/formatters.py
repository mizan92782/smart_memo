"""
logs/formatters.py — Colored Terminal Log Formatter

Features:
  ✅ Color-coded by HTTP status code (green 2xx, yellow 3xx, red 4xx/5xx)
  ✅ Format: API PATH | STATUS | USER ID | TIMESTAMP | DURATION
  ✅ 3-line spacing between log entries in terminal
  ✅ Plain text for file handlers (no ANSI codes)
"""
import logging
import datetime


# ─── ANSI Color Codes ─────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

# Status code colors
GREEN   = "\033[38;5;82m"    # 2xx Success
CYAN    = "\033[38;5;51m"    # 3xx Redirect
YELLOW  = "\033[38;5;220m"   # 4xx Client Error
RED     = "\033[38;5;196m"   # 5xx Server Error
MAGENTA = "\033[38;5;213m"   # Other / Unknown

# Meta colors
BLUE    = "\033[38;5;75m"    # API path
GREY    = "\033[38;5;245m"   # Timestamps, separators
WHITE   = "\033[38;5;255m"   # User ID, general info


def _status_color(status_code: int | None) -> str:
    """Return ANSI color code based on HTTP status code."""
    if status_code is None:
        return WHITE
    if 200 <= status_code < 300:
        return GREEN
    elif 300 <= status_code < 400:
        return CYAN
    elif 400 <= status_code < 500:
        return YELLOW
    elif status_code >= 500:
        return RED
    return MAGENTA


def _status_label(status_code: int | None) -> str:
    """Return a color-coded status code label."""
    color = _status_color(status_code)
    code = str(status_code) if status_code else "---"
    return f"{BOLD}{color}{code}{RESET}"


# ─── Colored Console Formatter ────────────────────────────────────────────────

class ColoredRequestFormatter(logging.Formatter):
    """
    Colored formatter for terminal output.
    Adds 3-line spacing between log entries for readability.

    Expected LogRecord extras (set by middleware):
        - status_code : int   HTTP response status code
        - api_path    : str   Request path (e.g., /auth/login/)
        - user_id     : str   User ID or "anonymous"
        - method      : str   HTTP method (GET, POST, etc.)
        - duration_ms : float Request duration in milliseconds
    """

    SEPARATOR = f"\n{GREY}{'─' * 80}{RESET}"

    def format(self, record: logging.LogRecord) -> str:
        # Extract request metadata from LogRecord extras
        status_code  = getattr(record, 'status_code', None)
        api_path     = getattr(record, 'api_path', record.getMessage())
        user_id      = getattr(record, 'user_id', 'anonymous')
        method       = getattr(record, 'method', 'GET')
        duration_ms  = getattr(record, 'duration_ms', None)

        # Timestamp
        ts = datetime.datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        # Compose colored log line
        status_str   = _status_label(status_code)
        method_color = CYAN if method in ('GET', 'HEAD') else MAGENTA
        method_str   = f"{BOLD}{method_color}{method:<6}{RESET}"
        path_str     = f"{BLUE}{api_path}{RESET}"
        user_str     = f"{WHITE}user:{user_id}{RESET}"
        ts_str       = f"{GREY}{ts}{RESET}"
        duration_str = f"{DIM}{duration_ms:.1f}ms{RESET}" if duration_ms is not None else ""

        line = (
            f"{method_str}  {path_str}  {status_str}  "
            f"{user_str}  {ts_str}  {duration_str}"
        )

        # Add level prefix for non-request logs
        if record.levelno >= logging.ERROR:
            level_color = RED
        elif record.levelno >= logging.WARNING:
            level_color = YELLOW
        else:
            level_color = GREY
        level_str = f"{level_color}[{record.levelname}]{RESET}"
        line = f"{level_str}  {line}"

        # 3-line spacing: blank line before + separator + blank line after
        return f"\n\n{self.SEPARATOR}\n{line}\n"


# ─── Plain File Formatter ─────────────────────────────────────────────────────

class PlainRequestFormatter(logging.Formatter):
    """
    Plain text formatter for file output (no ANSI codes).
    Same fields as ColoredRequestFormatter but machine-readable.
    """

    def format(self, record: logging.LogRecord) -> str:
        status_code = getattr(record, 'status_code', None)
        api_path    = getattr(record, 'api_path', record.getMessage())
        user_id     = getattr(record, 'user_id', 'anonymous')
        method      = getattr(record, 'method', 'GET')
        duration_ms = getattr(record, 'duration_ms', None)

        ts = datetime.datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        duration_str = f"{duration_ms:.1f}ms" if duration_ms is not None else "N/A"

        return (
            f"[{record.levelname}] {ts} | "
            f"{method} {api_path} | "
            f"status:{status_code} | "
            f"user:{user_id} | "
            f"duration:{duration_str}"
        )
