from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from stores.models.review_mod import StoreReview
from stores.serializers.review_ser import (
    StoreReviewSerializer,
    StoreReviewReplySerializer
)
from stores.services.review_service import ReviewService
from shared.permissions.permissions import IsVendor
from shared.responses.responses import custome_success_response, custome_error_response


class StoreReviewViewSet(viewsets.GenericViewSet):
    """
    Dedicated viewset for review-level interactions:
    - Vendor replies to customer reviews
    - Review deletion by customer author or staff
    """
    queryset = StoreReview.objects.all()
    serializer_class = StoreReviewSerializer

    def get_permissions(self):
        if self.action == 'reply':
            return [IsAuthenticated(), IsVendor()]
        return [IsAuthenticated()]

    def destroy(self, request, pk=None):
        """DELETE /stores/reviews/{id}/ -> Delete review by author or admin."""
        try:
            ReviewService.delete_review(actor=request.user, review_id=pk)
            return custome_success_response(message="Review deleted successfully.")
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_404_NOT_FOUND)
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """POST /stores/reviews/{id}/reply/ -> Store vendor replies to a review."""
        serializer = StoreReviewReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reply_text = serializer.validated_data['reply']
        try:
            review = ReviewService.reply_to_review(
                actor=request.user,
                review_id=pk,
                reply_text=reply_text
            )
            return custome_success_response(
                message="Reply posted successfully.",
                data=StoreReviewSerializer(review).data
            )
        except ValueError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)
        except PermissionError as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
