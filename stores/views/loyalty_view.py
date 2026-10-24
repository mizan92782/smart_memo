from django.core.exceptions import PermissionDenied
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from shared.responses.responses import custome_success_response, custome_error_response
from stores.models.store_mod import Store
from stores.services.loyalty_service import LoyaltyService
from stores.repositories.loyalty_repository import LoyaltyRepository
from stores.serializers.loyalty_ser import (
    StoreLoyaltyProgramSerializer,
    CustomerStoreLoyaltySerializer,
    LoyaltyTransactionSerializer
)


class StoreLoyaltyProgramView(APIView):
    """
    Manage store loyalty program configuration.
    GET: Retrieve loyalty program rules for a store (AllowAny).
    PUT/PATCH: Vendor configures loyalty program rules (Vendor/Staff only).
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get(self, request, store_id):
        store = Store.objects.filter(id=store_id, is_deleted=False).first()
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        program = LoyaltyService.get_or_create_program(store=store)
        return custome_success_response(
            message="Store loyalty program retrieved.",
            data=StoreLoyaltyProgramSerializer(program).data
        )

    def put(self, request, store_id):
        return self.patch(request, store_id)

    def patch(self, request, store_id):
        store = Store.objects.filter(id=store_id, is_deleted=False).first()
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        try:
            program = LoyaltyService.update_program(store=store, vendor=request.user, data=request.data)
            return custome_success_response(
                message="Store loyalty program updated successfully.",
                data=StoreLoyaltyProgramSerializer(program).data
            )
        except (PermissionDenied, PermissionError) as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            return custome_error_response(str(exc), status_code=status.HTTP_400_BAD_REQUEST)


class CustomerStoreLoyaltyView(APIView):
    """
    Customer inspects their store-scoped loyalty card, stamp punch progress, and transaction history.
    GET /stores/{id}/loyalty/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        store = Store.objects.filter(id=store_id, is_deleted=False).first()
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        summary = LoyaltyService.get_customer_store_loyalty_summary(customer=request.user, store=store)
        return custome_success_response(
            message=f"Loyalty card summary for '{store.name}'.",
            data=summary
        )


class VendorStoreLoyalCustomersView(APIView):
    """
    Vendor inspects their top loyal customers and loyalty metrics for a store.
    GET /stores/{id}/loyalty-customers/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, store_id):
        store = Store.objects.filter(id=store_id, is_deleted=False).first()
        if not store:
            return custome_error_response("Store not found.", status_code=status.HTTP_404_NOT_FOUND)

        if store.vendor_id != request.user.id and not getattr(request.user, 'is_staff', False):
            return custome_error_response("You do not have permission to view customer loyalty data for this store.", status_code=status.HTTP_403_FORBIDDEN)

        customers = LoyaltyRepository.get_store_loyal_customers(store_id=store.id)
        return custome_success_response(
            message="Loyal customers retrieved.",
            data=CustomerStoreLoyaltySerializer(customers, many=True).data
        )


class CustomerAllLoyaltyCardsView(APIView):
    """
    Customer views all active store punch cards and loyalty accounts across all stores they visit.
    GET /users/loyalty-cards/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        loyalties = LoyaltyRepository.get_all_customer_loyalties(customer_id=request.user.id)
        return custome_success_response(
            message="Customer loyalty cards retrieved.",
            data=CustomerStoreLoyaltySerializer(loyalties, many=True).data
        )
