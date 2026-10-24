from rest_framework.exceptions import NotFound, ValidationError
from users.models.address_mod import CustomerAddress
from users.repositories.address_repository import AddressRepository


class AddressService:
    """Service layer for customer saved delivery addresses."""

    @staticmethod
    def _validate_coordinates(lat, lng):
        if lat is not None:
            if not (-90.0 <= float(lat) <= 90.0):
                raise ValidationError("Latitude must be between -90.0 and 90.0 degrees.")
        if lng is not None:
            if not (-180.0 <= float(lng) <= 180.0):
                raise ValidationError("Longitude must be between -180.0 and 180.0 degrees.")

    @staticmethod
    def create_address(customer, validated_data: dict) -> CustomerAddress:
        lat = validated_data.get('latitude')
        lng = validated_data.get('longitude')
        AddressService._validate_coordinates(lat, lng)
        return AddressRepository.create_address(customer, **validated_data)

    @staticmethod
    def update_address(customer, address_id: int, validated_data: dict) -> CustomerAddress:
        address = AddressRepository.get_address(customer, address_id)
        if not address:
            raise NotFound("Address not found or does not belong to you.")
        lat = validated_data.get('latitude', address.latitude)
        lng = validated_data.get('longitude', address.longitude)
        AddressService._validate_coordinates(lat, lng)
        return AddressRepository.update_address(address, **validated_data)

    @staticmethod
    def set_default_address(customer, address_id: int) -> CustomerAddress:
        address = AddressRepository.get_address(customer, address_id)
        if not address:
            raise NotFound("Address not found or does not belong to you.")
        return AddressRepository.set_default(customer, address)

    @staticmethod
    def delete_address(customer, address_id: int) -> None:
        address = AddressRepository.get_address(customer, address_id)
        if not address:
            raise NotFound("Address not found or does not belong to you.")
        AddressRepository.soft_delete_address(address)
