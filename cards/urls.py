from django.urls import path, include
from rest_framework.routers import DefaultRouter
from cards.views.card_view import CardViewSet
from cards.views.template_view import StoreMemoTemplateViewSet

router = DefaultRouter()
router.register(r'templates', StoreMemoTemplateViewSet, basename='template')
router.register(r'', CardViewSet, basename='card')

urlpatterns = [
    path('', include(router.urls)),
]
