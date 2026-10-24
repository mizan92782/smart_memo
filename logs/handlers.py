"""
logs/handlers.py — Custom Log Handlers

Provides configured handlers for:
  - Console (colored terminal output)
  - File (plain text for aggregation/storage)
"""
import logging
import logging.handlers
import os
from pathlib import Path


def get_console_handler() -> logging.StreamHandler:
    """
    Returns a StreamHandler configured with the ColoredRequestFormatter.
    Use for terminal output during development and production.
    """
    from logs.formatters import ColoredRequestFormatter
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredRequestFormatter())
    handler.setLevel(logging.DEBUG)
    return handler


def get_file_handler(log_file: str = "logs/app.log") -> logging.handlers.RotatingFileHandler:
    """
    Returns a RotatingFileHandler configured with the PlainRequestFormatter.
    Rotates at 10MB, keeps 5 backup files.
    Use for persistent log storage and aggregation (e.g., Loki).

    Args:
        log_file: Path to the log file.
    """
    from logs.formatters import PlainRequestFormatter

    # Ensure log directory exists
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8',
    )
    handler.setFormatter(PlainRequestFormatter())
    handler.setLevel(logging.INFO)
    return handler


def get_error_file_handler(log_file: str = "logs/errors.log") -> logging.handlers.RotatingFileHandler:
    """
    Returns a RotatingFileHandler for ERROR-level logs only.
    Useful for alerting systems that watch for errors.
    """
    from logs.formatters import PlainRequestFormatter

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=10,
        encoding='utf-8',
    )
    handler.setFormatter(PlainRequestFormatter())
    handler.setLevel(logging.ERROR)
    return handler
