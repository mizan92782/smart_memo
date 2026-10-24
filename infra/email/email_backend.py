"""
infra/email/email_backend.py — Dynamic Database-Backed Email Backend

This backend reads SMTP configuration from the database (EmailConfiguration model)
and applies it at runtime, overriding environment variable settings.

How it works:
1. On each email send, it fetches the singleton EmailConfiguration from the DB.
2. If a DB config exists and is populated, it uses those SMTP credentials.
3. If no DB config exists, it falls back to Django settings (environment variables).

Usage in settings.py:
    EMAIL_BACKEND = 'infra.email.email_backend.DynamicDatabaseEmailBackend'
"""
import logging
from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger(__name__)


class DynamicDatabaseEmailBackend(EmailBackend):
    """
    SMTP email backend that loads credentials dynamically from the database.
    Falls back to Django settings if no DB configuration exists.
    """

    def __init__(self, *args, **kwargs):
        # Load DB config on initialization
        config = self._load_db_config()
        if config:
            kwargs.setdefault('host', config['EMAIL_HOST'])
            kwargs.setdefault('port', config['EMAIL_PORT'])
            kwargs.setdefault('username', config['EMAIL_HOST_USER'])
            kwargs.setdefault('password', config['EMAIL_HOST_PASSWORD'])
            kwargs.setdefault('use_tls', config['EMAIL_USE_TLS'])
        super().__init__(*args, **kwargs)

    @staticmethod
    def _load_db_config() -> dict | None:
        """
        Load SMTP configuration from the database.
        Returns a config dict, or None if DB config is unavailable.
        """
        try:
            from configuration.services.email_config import get_active_email_config
            config = get_active_email_config()
            if config.get('EMAIL_HOST_USER') and config.get('EMAIL_HOST'):
                return config
        except Exception as exc:
            logger.warning("DynamicDatabaseEmailBackend: could not load DB config — %s", str(exc))
        return None
