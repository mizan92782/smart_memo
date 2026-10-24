from django.urls import path, include
from rest_framework.routers import DefaultRouter
from cards.views.card_view import CardViewSet

router = DefaultRouter()
router.register(r'', CardViewSet, basename='card')

urlpatterns = [
    path('', include(router.urls)),
]
