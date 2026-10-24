"""
Shared Permissions — Custom permission classes for project-wide use.

All custom permission classes should live here.
Import from here rather than defining permissions in individual apps.
"""
from rest_framework.permissions import BasePermission
from shared.enums.enums import UserRoleEnum


class IsAdmin(BasePermission):
    """
    Allows access only to superusers (admin users).
    Usage: permission_classes = [IsAdmin]
    """
    message = "Only super administrators can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_superuser or getattr(request.user, 'role', None) == UserRoleEnum.SUPERUSER)
        )


class IsStaffOrAdmin(BasePermission):
    """
    Allows access to staff users and superusers.
    """
    message = "Only staff or administrators can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_staff
                or request.user.is_superuser
                or getattr(request.user, 'role', None) in (UserRoleEnum.STAFF, UserRoleEnum.SUPERUSER)
            )
        )



class IsOwner(BasePermission):
    """
    Object-level permission: only allows access to the owner of an object.
    The object must have a `user` field pointing to the request user.
    """
    message = "You can only access your own resources."

    def has_object_permission(self, request, view, obj):
        return hasattr(obj, 'user') and obj.user == request.user


class IsOwnerOrAdmin(BasePermission):
    """
    Allows object-level access if the user is the owner OR an admin.
    """
    message = "You can only access your own resources or must be an admin."

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return hasattr(obj, 'user') and obj.user == request.user


class IsReadOnly(BasePermission):
    """
    Allows only safe (read-only) HTTP methods: GET, HEAD, OPTIONS.
    """
    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

    def has_permission(self, request, view):
        return request.method in self.SAFE_METHODS


class IsAuthenticatedOrReadOnly(BasePermission):
    """
    Allows read-only access to anyone, full access to authenticated users.
    """
    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

    def has_permission(self, request, view):
        if request.method in self.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)


from shared.enums.enums import UserRoleEnum


class IsVendor(BasePermission):
    """Allows access only to authenticated users with VENDOR role or admins."""
    message = "Only store vendors can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (getattr(request.user, 'role', None) == UserRoleEnum.VENDOR or request.user.is_staff or request.user.is_superuser)
        )


class IsCustomer(BasePermission):
    """Allows access to authenticated customers."""
    message = "Only customer accounts can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (getattr(request.user, 'role', None) in (UserRoleEnum.CUSTOMER, UserRoleEnum.USER) or request.user.is_superuser)
        )


class IsStoreOwner(BasePermission):
    """
    Object-level permission ensuring the actor is the owner/vendor of the store.
    Handles Store objects directly, or objects linked via a `store` attribute.
    """
    message = "You can only manage your own store and store-scoped data."

    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        if hasattr(obj, 'vendor'):
            return obj.vendor == request.user
        if hasattr(obj, 'store') and hasattr(obj.store, 'vendor'):
            return obj.store.vendor == request.user
        return False
