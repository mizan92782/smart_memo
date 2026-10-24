from typing import Optional, Tuple
from django.db.models import QuerySet
from django.utils import timezone
from notifications.models.notification_mod import Notification, NotificationType


class NotificationRepository:
    """Handles pure database queries for Notification entities (static methods only)."""

    @staticmethod
    def get_by_id(notification_id: int) -> Optional[Notification]:
        return Notification.objects.filter(pk=notification_id, is_deleted=False).select_related('recipient', 'store').first()

    @staticmethod
    def get_by_recipient(recipient_id: int, unread_only: bool = False) -> QuerySet[Notification]:
        qs = Notification.objects.filter(
            recipient_id=recipient_id,
            is_deleted=False
        ).select_related('store')
        if unread_only:
            qs = qs.filter(is_read=False)
        return qs

    @staticmethod
    def get_unread_count(recipient_id: int) -> int:
        return Notification.objects.filter(
            recipient_id=recipient_id,
            is_read=False,
            is_deleted=False
        ).count()

    @staticmethod
    def create_notification(
        recipient,
        title: str,
        message: str,
        notification_type: str = NotificationType.SYSTEM,
        store=None,
        metadata: dict = None,
        idempotency_key: str = None
    ) -> Tuple[Notification, bool]:
        """Creates notification or returns existing if idempotency_key is present."""
        if metadata is None:
            metadata = {}

        if idempotency_key:
            existing = Notification.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing, False

        notification = Notification.objects.create(
            recipient=recipient,
            store=store,
            title=title,
            message=message,
            notification_type=notification_type,
            metadata=metadata,
            idempotency_key=idempotency_key
        )
        return notification, True

    @staticmethod
    def mark_as_read(notification: Notification) -> Notification:
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at', 'updated_at'])
        return notification

    @staticmethod
    def mark_all_as_read(recipient_id: int) -> int:
        now = timezone.now()
        updated_count = Notification.objects.filter(
            recipient_id=recipient_id,
            is_read=False,
            is_deleted=False
        ).update(is_read=True, read_at=now, updated_at=now)
        return updated_count

    @staticmethod
    def delete_notification(notification: Notification) -> None:
        notification.soft_delete()
