from django.urls import path, include
from rest_framework.routers import DefaultRouter
from stores.views.store_view import StoreViewSet
from stores.views.review_view import StoreReviewViewSet
from stores.views.coupon_view import CouponViewSet
from stores.views.loyalty_view import (
    StoreLoyaltyProgramView,
    CustomerStoreLoyaltyView,
    VendorStoreLoyalCustomersView
)

router = DefaultRouter()
router.register(r'reviews', StoreReviewViewSet, basename='store-review')
router.register(r'coupons', CouponViewSet, basename='store-coupon')
router.register(r'', StoreViewSet, basename='store')

urlpatterns = [
    path('<int:store_id>/loyalty-program/', StoreLoyaltyProgramView.as_view(), name='store-loyalty-program'),
    path('<int:store_id>/loyalty/', CustomerStoreLoyaltyView.as_view(), name='customer-store-loyalty'),
    path('<int:store_id>/loyalty-customers/', VendorStoreLoyalCustomersView.as_view(), name='vendor-store-loyal-customers'),
    path('', include(router.urls)),
]

