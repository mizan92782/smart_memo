import logging
from django.db import transaction
from django.db.models import QuerySet
from notifications.models.notification_mod import Notification, NotificationType
from notifications.repositories.notification_repository import NotificationRepository
from notifications.tasks import send_notification_email_task

logger = logging.getLogger(__name__)


class NotificationService:
    """Encapsulates business operations for system and store notifications."""

    @staticmethod
    def create_notification(
        recipient,
        title: str,
        message: str,
        notification_type: str = NotificationType.SYSTEM,
        store=None,
        metadata: dict = None,
        idempotency_key: str = None
    ) -> Notification:
        """
        Creates a notification record and schedules background email delivery safely
        after transaction commit.
        """
        notification, created = NotificationRepository.create_notification(
            recipient=recipient,
            store=store,
            title=title,
            message=message,
            notification_type=notification_type,
            metadata=metadata,
            idempotency_key=idempotency_key
        )

        if created:
            def dispatch_task():
                try:
                    send_notification_email_task.delay(notification.id)
                except Exception as exc:
                    logger.warning("Could not dispatch async notification task: %s", exc)

            transaction.on_commit(dispatch_task)

        return notification

    @staticmethod
    def notify_order_submitted(order) -> Notification:
        """Notifies store vendor about new order submission."""
        return NotificationService.create_notification(
            recipient=order.store.vendor,
            store=order.store,
            title=f"New Order #{order.order_number}",
            message=(
                f"A new order #{order.order_number} has been placed for store '{order.store.name}' "
                f"by {order.customer.email}. Total amount: {order.total_amount}."
            ),
            notification_type=NotificationType.ORDER_SUBMITTED,
            metadata={
                'order_id': order.id,
                'order_number': order.order_number,
                'total_amount': str(order.total_amount),
                'fulfillment_type': order.fulfillment_type
            },
            idempotency_key=f"order_submitted_{order.id}"
        )

    @staticmethod
    def notify_order_status_change(order, new_status: str) -> Notification:
        """Notifies customer about order progress / cancellation."""
        type_mapping = {
            'accepted': NotificationType.ORDER_ACCEPTED,
            'completed': NotificationType.ORDER_COMPLETED,
            'cancelled': NotificationType.ORDER_CANCELLED,
            'rejected': NotificationType.ORDER_CANCELLED,
        }
        notif_type = type_mapping.get(new_status, NotificationType.SYSTEM)

        return NotificationService.create_notification(
            recipient=order.customer,
            store=order.store,
            title=f"Order #{order.order_number} Update",
            message=f"Your order #{order.order_number} at '{order.store.name}' has been updated to '{new_status}'.",
            notification_type=notif_type,
            metadata={
                'order_id': order.id,
                'order_number': order.order_number,
                'status': new_status
            },
            idempotency_key=f"order_status_{order.id}_{new_status}"
        )

    @staticmethod
    def notify_low_stock_if_needed(store, product, balance) -> Notification | None:
        """Dispatches an alert to vendor if balance falls to or below threshold."""
        if not balance.is_low_stock:
            return None

        # Snap to integer or 3 decimals for idempotency key
        avail_str = f"{balance.available:.3f}"
        return NotificationService.create_notification(
            recipient=store.vendor,
            store=store,
            title=f"Low Stock Alert: {product.name}",
            message=(
                f"Stock for '{product.name}' (SKU: {product.sku or 'N/A'}) in store '{store.name}' "
                f"is running low. Available: {balance.available}, Low-stock threshold: {balance.low_stock_threshold}."
            ),
            notification_type=NotificationType.LOW_STOCK_ALERT,
            metadata={
                'product_id': product.id,
                'product_name': product.name,
                'available': str(balance.available),
                'threshold': str(balance.low_stock_threshold)
            },
            idempotency_key=f"low_stock_{store.id}_{product.id}_{avail_str}"
        )

    @staticmethod
    def mark_as_read(notification_id: int, user) -> Notification:
        notification = NotificationRepository.get_by_id(notification_id)
        if not notification:
            raise ValueError("Notification not found.")

        if notification.recipient != user and not user.is_superuser:
            raise PermissionError("You can only access your own notifications.")

        return NotificationRepository.mark_as_read(notification)

    @staticmethod
    def mark_all_as_read(user) -> int:
        return NotificationRepository.mark_all_as_read(user.id)

    @staticmethod
    def get_user_notifications(user, unread_only: bool = False) -> QuerySet[Notification]:
        return NotificationRepository.get_by_recipient(user.id, unread_only=unread_only)

    @staticmethod
    def get_unread_count(user) -> int:
        return NotificationRepository.get_unread_count(user.id)
