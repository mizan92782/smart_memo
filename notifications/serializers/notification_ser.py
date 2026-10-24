from rest_framework import serializers
from notifications.models.notification_mod import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for user notifications."""
    store_name = serializers.CharField(source='store.name', read_only=True, default=None)

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message',
            'is_read', 'read_at', 'store', 'store_name',
            'metadata', 'created_at'
        ]
        read_only_fields = [
            'id', 'notification_type', 'title', 'message',
            'read_at', 'store', 'store_name', 'metadata', 'created_at'
        ]
