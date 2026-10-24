from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from users.serializers.address_ser import CustomerAddressSerializer
from users.repositories.address_repository import AddressRepository
from users.services.address_service import AddressService
from shared.responses.responses import custome_success_response, custome_error_response


class CustomerAddressViewSet(viewsets.ModelViewSet):
    """
    CRUD viewset for customer saved delivery addresses.
    Strictly isolated to authenticated customer:
    Customer A can never view, update, or delete Customer B's addresses.
    """
    serializer_class = CustomerAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AddressRepository.list_customer_addresses(self.request.user)

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address = AddressService.create_address(request.user, serializer.validated_data)
        return custome_success_response(
            message="Address created successfully.",
            data=self.get_serializer(address).data,
            status_code=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        address = AddressService.update_address(request.user, kwargs.get('pk'), serializer.validated_data)
        return custome_success_response(
            message="Address updated successfully.",
            data=self.get_serializer(address).data
        )

    def destroy(self, request, *args, **kwargs):
        AddressService.delete_address(request.user, kwargs.get('pk'))
        return custome_success_response(
            message="Address deleted successfully.",
            status_code=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, pk=None):
        address = AddressService.set_default_address(request.user, pk)
        return custome_success_response(
            message="Address set as default.",
            data=self.get_serializer(address).data
        )
