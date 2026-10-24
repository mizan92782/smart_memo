from rest_framework import viewsets, permissions
from audit.serializers.audit_ser import AuditLogSerializer
from audit.services.audit_service import AuditService


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint for tenant-isolated audit log inspection.
    - Staff / Admin: Can view all audit entries or filter by store.
    - Vendor: Restricted strictly to audit logs of their owned stores.
    - Customer / Anonymous: Access denied (403 Forbidden).
    """
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        store_id = self.request.query_params.get('store_id')
        queryset = AuditService.get_audit_logs_for_actor(self.request.user, store_id=store_id)

        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)

        target_model = self.request.query_params.get('target_model')
        if target_model:
            queryset = queryset.filter(target_model=target_model)

        target_id = self.request.query_params.get('target_id')
        if target_id:
            queryset = queryset.filter(target_id=target_id)

        return queryset
