from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from notifications.models.notification_mod import Notification
from notifications.serializers.notification_ser import NotificationSerializer
from notifications.services.notification_service import NotificationService
from shared.responses.responses import custome_success_response, custome_error_response
from shared.pagination.pagination import StandardResultsPagination


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user notification feed, unread tracking, and read state management.
    Strictly isolated to authenticated request.user.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Notification.objects.none()
        unread_only = self.request.query_params.get('unread_only', '').lower() in ('true', '1')
        return NotificationService.get_user_notifications(self.request.user, unread_only=unread_only)

    @action(detail=True, methods=['patch', 'post'])
    def read(self, request, pk=None):
        """Mark a single notification as read."""
        try:
            notification = NotificationService.mark_as_read(notification_id=pk, user=request.user)
            return custome_success_response(
                message="Notification marked as read.",
                data=NotificationSerializer(notification).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_404_NOT_FOUND)
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """Mark all unread notifications as read for current user."""
        count = NotificationService.mark_all_as_read(user=request.user)
        return custome_success_response(
            message=f"Marked {count} notifications as read.",
            data={'marked_count': count}
        )

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """Get the count of unread notifications for notification badge UI."""
        count = NotificationService.get_unread_count(user=request.user)
        return custome_success_response(
            message="Unread notification count retrieved.",
            data={'unread_count': count}
        )
