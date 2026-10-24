from rest_framework import serializers
from users.models.address_mod import CustomerAddress


class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = [
            'id',
            'label',
            'recipient_name',
            'phone_number',
            'address_line',
            'city',
            'postal_code',
            'latitude',
            'longitude',
            'delivery_instructions',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
