from rest_framework import serializers
from stores.models.store_mod import Store
from shared.base.base_serializer import BaseModelSerializer


class StoreSerializer(BaseModelSerializer):
    """Full serializer for Store management by vendor and platform admins."""
    vendor_email = serializers.EmailField(source='vendor.email', read_only=True)

    class Meta:
        model = Store
        fields = [
            'id', 'name', 'slug', 'description', 'phone_number', 'email',
            'address', 'latitude', 'longitude', 'is_active',
            'is_verified', 'verified_at', 'verification_notes',
            'opening_time', 'closing_time', 'delivery_enabled',
            'pickup_enabled', 'delivery_fee', 'min_order_amount',
            'vendor_email', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'created_at', 'updated_at', 'vendor_email',
            'is_verified', 'verified_at', 'verification_notes'
        ]



from stores.models.favorite_mod import FavoriteStore


class PublicStoreSerializer(serializers.ModelSerializer):
    """Public customer-facing store discovery serializer (no private financials)."""
    distance_km = serializers.FloatField(read_only=True, required=False, default=None)
    is_favorite = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Store
        fields = [
            'id', 'name', 'slug', 'description', 'phone_number', 'email',
            'address', 'latitude', 'longitude', 'is_active',
            'opening_time', 'closing_time', 'delivery_enabled',
            'pickup_enabled', 'delivery_fee', 'min_order_amount',
            'distance_km', 'is_favorite'
        ]

    def get_is_favorite(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        # If pre-annotated on queryset:
        if hasattr(obj, 'is_favorite_flag'):
            return bool(obj.is_favorite_flag)
        from stores.services.favorite_service import FavoriteService
        return FavoriteService.is_store_favorite(request.user, obj.id)


class FavoriteStoreSerializer(serializers.ModelSerializer):
    """Serializer for customer's favorite stores."""
    store = PublicStoreSerializer(read_only=True)

    class Meta:
        model = FavoriteStore
        fields = ['id', 'store', 'created_at']
        read_only_fields = ['id', 'store', 'created_at']

