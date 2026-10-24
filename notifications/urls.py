from django.urls import path, include
from rest_framework.routers import DefaultRouter
from notifications.views.notification_view import NotificationViewSet

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
