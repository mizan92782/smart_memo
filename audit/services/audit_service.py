import logging
from rest_framework.exceptions import PermissionDenied, NotFound
from shared.enums.enums import UserRoleEnum
from stores.repositories.store_repository import StoreRepository
from audit.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    """Domain service managing immutable audit trails and tenant authorization checks."""

    @staticmethod
    def _extract_ip(request):
        if not request:
            return None
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @staticmethod
    def _extract_user_agent(request):
        if not request:
            return ''
        return request.META.get('HTTP_USER_AGENT', '')[:500]

    @staticmethod
    def log(
        action: str,
        target_model: str,
        target_id,
        actor=None,
        store=None,
        details: dict = None,
        request=None
    ):
        """
        Safely records an audit entry. Never raises exceptions to caller
        to avoid breaking the primary business transaction.
        """
        try:
            if actor is None and request and getattr(request, 'user', None) and request.user.is_authenticated:
                actor = request.user

            ip_address = AuditService._extract_ip(request)
            user_agent = AuditService._extract_user_agent(request)

            return AuditRepository.create_entry(
                action=action,
                target_model=target_model,
                target_id=str(target_id),
                actor=actor,
                store=store,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
        except Exception as exc:
            logger.error(f"[AuditService] Failed to record audit log: {exc}", exc_info=True)
            return None

    @staticmethod
    def get_audit_logs_for_actor(actor, store_id=None):
        """
        Returns audit log queryset strictly isolated by actor permissions:
        - Staff / Admin: platform-wide or filtered by store
        - Vendor: strictly limited to vendor-owned stores
        - Customer / Unauthenticated: forbidden
        """
        if not actor or not actor.is_authenticated:
            raise PermissionDenied("Authentication required to access audit trails.")

        is_staff_or_admin = (
            actor.is_staff or
            getattr(actor, 'role', '') in (UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER)
        )

        if is_staff_or_admin:
            queryset = AuditRepository.get_all_logs()
            if store_id:
                queryset = queryset.filter(store_id=store_id)
            return queryset

        is_vendor = (
            getattr(actor, 'role', '') == UserRoleEnum.VENDOR or
            getattr(actor, 'is_vendor', False)
        )

        if is_vendor:
            if store_id:
                store = StoreRepository.get_by_id(store_id)
                if not store:
                    raise NotFound("Store not found.")
                if store.vendor != actor:
                    raise PermissionDenied("You do not have permission to view audit logs for this store.")
                return AuditRepository.get_logs_for_store(store)
            return AuditRepository.get_logs_for_vendor(actor)

        raise PermissionDenied("Customers do not have permission to view audit logs.")
