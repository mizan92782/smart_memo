from rest_framework import serializers
from audit.models.audit_mod import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'store',
            'store_name',
            'actor',
            'actor_email',
            'actor_role',
            'action',
            'target_model',
            'target_id',
            'ip_address',
            'user_agent',
            'details',
            'created_at',
        ]
        read_only_fields = fields
