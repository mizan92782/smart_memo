from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from stores.models.coupon_mod import Coupon
from stores.serializers.coupon_ser import CouponSerializer, CouponUsageSerializer
from stores.services.coupon_service import CouponService
from stores.repositories.coupon_repository import CouponRepository
from shared.permissions.permissions import IsVendor
from shared.responses.responses import custome_success_response, custome_error_response


class CouponViewSet(viewsets.GenericViewSet):
    """
    Dedicated viewset for coupon management:
    - GET /stores/coupons/{id}/
    - PATCH /stores/coupons/{id}/
    - DELETE /stores/coupons/{id}/
    - GET /stores/coupons/{id}/usages/
    """
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def retrieve(self, request, pk=None):
        """GET /stores/coupons/{id}/ -> Retrieve coupon details."""
        coupon = CouponRepository.get_by_id(pk)
        if not coupon:
            return custome_error_response("Coupon not found.", status_code=status.HTTP_404_NOT_FOUND)

        is_staff = request.user.is_staff or request.user.is_superuser
        if coupon.store.vendor != request.user and not is_staff:
            return custome_error_response("You do not have permission to view this coupon.", status_code=status.HTTP_403_FORBIDDEN)

        return custome_success_response(
            message="Coupon retrieved successfully.",
            data=CouponSerializer(coupon).data
        )

    def partial_update(self, request, pk=None):
        """PATCH /stores/coupons/{id}/ -> Update coupon settings."""
        try:
            coupon = CouponService.update_coupon(
                coupon_id=pk,
                actor=request.user,
                data=request.data
            )
            return custome_success_response(
                message="Coupon updated successfully.",
                data=CouponSerializer(coupon).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, pk=None):
        """DELETE /stores/coupons/{id}/ -> Delete coupon."""
        try:
            CouponService.delete_coupon(coupon_id=pk, actor=request.user)
            return custome_success_response(message="Coupon deleted successfully.")
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_404_NOT_FOUND)
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['get'])
    def usages(self, request, pk=None):
        """GET /stores/coupons/{id}/usages/ -> View redemption history."""
        coupon = CouponRepository.get_by_id(pk)
        if not coupon:
            return custome_error_response("Coupon not found.", status_code=status.HTTP_404_NOT_FOUND)

        is_staff = request.user.is_staff or request.user.is_superuser
        if coupon.store.vendor != request.user and not is_staff:
            return custome_error_response("You do not have permission to view usages for this coupon.", status_code=status.HTTP_403_FORBIDDEN)

        usages = CouponRepository.get_coupon_usages(coupon.id)
        return custome_success_response(
            message="Coupon usages retrieved successfully.",
            data=CouponUsageSerializer(usages, many=True).data
        )
