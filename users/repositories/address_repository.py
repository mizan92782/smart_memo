from django.db import transaction
from users.models.address_mod import CustomerAddress


class AddressRepository:
    """Static-only repository for querying and managing CustomerAddress records."""

    @staticmethod
    def create_address(customer, **data) -> CustomerAddress:
        is_default = data.get('is_default', False)
        with transaction.atomic():
            if is_default:
                CustomerAddress.objects.filter(customer=customer, is_default=True).update(is_default=False)
            elif not CustomerAddress.objects.filter(customer=customer, is_deleted=False).exists():
                # First address is automatically default
                data['is_default'] = True
            return CustomerAddress.objects.create(customer=customer, **data)

    @staticmethod
    def list_customer_addresses(customer):
        return CustomerAddress.objects.filter(customer=customer, is_deleted=False)

    @staticmethod
    def get_address(customer, address_id) -> CustomerAddress | None:
        try:
            return CustomerAddress.objects.get(id=address_id, customer=customer, is_deleted=False)
        except CustomerAddress.DoesNotExist:
            return None

    @staticmethod
    def get_default_address(customer) -> CustomerAddress | None:
        return CustomerAddress.objects.filter(customer=customer, is_default=True, is_deleted=False).first()

    @staticmethod
    def update_address(address: CustomerAddress, **data) -> CustomerAddress:
        is_default = data.get('is_default')
        with transaction.atomic():
            if is_default:
                CustomerAddress.objects.filter(customer=address.customer, is_default=True).exclude(id=address.id).update(is_default=False)
            for key, value in data.items():
                setattr(address, key, value)
            address.save()
            return address

    @staticmethod
    def set_default(customer, address: CustomerAddress) -> CustomerAddress:
        with transaction.atomic():
            CustomerAddress.objects.filter(customer=customer, is_default=True).update(is_default=False)
            address.is_default = True
            address.save(update_fields=['is_default', 'updated_at'])
            return address

    @staticmethod
    def soft_delete_address(address: CustomerAddress) -> None:
        with transaction.atomic():
            was_default = address.is_default
            address.soft_delete()
            if was_default:
                next_addr = CustomerAddress.objects.filter(customer=address.customer, is_deleted=False).first()
                if next_addr:
                    next_addr.is_default = True
                    next_addr.save(update_fields=['is_default', 'updated_at'])
