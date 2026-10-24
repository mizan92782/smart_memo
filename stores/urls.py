from django.urls import path, include
from rest_framework.routers import DefaultRouter
from stores.views.store_view import StoreViewSet
from stores.views.review_view import StoreReviewViewSet

router = DefaultRouter()
router.register(r'reviews', StoreReviewViewSet, basename='store-review')
router.register(r'', StoreViewSet, basename='store')

urlpatterns = [
    path('', include(router.urls)),
]
