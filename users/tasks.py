"""
users/tasks.py — Background Tasks (Celery) for Users
"""
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def send_welcome_email_task(user_email: str, full_name: str = ""):
    """Send a welcome email asynchronously to a newly registered user."""
    subject = "Welcome to Smart Memo!"
    message = f"Hello {full_name or user_email},\n\nWelcome to Smart Memo! Your account has been created successfully."
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@smartmemo.com'),
            recipient_list=[user_email],
            fail_silently=False,
        )
        logger.info("Welcome email sent to %s", user_email)
    except Exception as exc:
        logger.error("Failed to send welcome email to %s: %s", user_email, str(exc))
