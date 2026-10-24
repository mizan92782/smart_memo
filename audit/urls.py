from django.urls import path, include
from rest_framework.routers import DefaultRouter
from audit.views.audit_view import AuditLogViewSet

router = DefaultRouter()
router.register(r'logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', include(router.urls)),
]
