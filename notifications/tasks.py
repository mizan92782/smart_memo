import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from notifications.repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_email_task(self, notification_id: int):
    """
    Asynchronous Celery task to deliver email notification to the recipient.
    Designed with error catching and safe retry handling.
    """
    notification = NotificationRepository.get_by_id(notification_id)
    if not notification:
        logger.warning("Notification with id %s not found. Skipping email.", notification_id)
        return False

    recipient_email = notification.recipient.email
    if not recipient_email:
        logger.warning("Recipient for notification %s has no email.", notification_id)
        return False

    subject = f"[Smart Memo] {notification.title}"
    body = f"Hello,\n\n{notification.message}\n\nThank you for using Smart Memo!"

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@smartmemo.com'),
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        logger.info("Notification email delivered to %s for notification %s", recipient_email, notification_id)
        return True
    except Exception as exc:
        logger.error(
            "Failed to send email for notification %s to %s: %s",
            notification_id, recipient_email, str(exc)
        )
        # Safe retry if Celery worker is active
        try:
            raise self.retry(exc=exc)
        except Exception:
            return False
