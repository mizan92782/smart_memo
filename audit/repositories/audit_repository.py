from audit.models.audit_mod import AuditLog


class AuditRepository:
    """Static-only repository for querying and creating audit log entries."""

    @staticmethod
    def create_entry(
        action: str,
        target_model: str,
        target_id: str,
        actor=None,
        store=None,
        details: dict = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> AuditLog:
        actor_email = actor.email if actor and hasattr(actor, 'email') else ''
        actor_role = actor.role if actor and hasattr(actor, 'role') else ''

        return AuditLog.objects.create(
            action=action,
            target_model=target_model,
            target_id=str(target_id),
            actor=actor if actor and getattr(actor, 'is_authenticated', False) else None,
            actor_email=actor_email,
            actor_role=actor_role,
            store=store,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent or ''
        )

    @staticmethod
    def get_all_logs():
        return AuditLog.objects.select_related('store', 'actor').all()

    @staticmethod
    def get_logs_for_store(store):
        return AuditLog.objects.filter(store=store).select_related('store', 'actor')

    @staticmethod
    def get_logs_for_vendor(vendor_user):
        return AuditLog.objects.filter(store__vendor=vendor_user).select_related('store', 'actor')
