from rest_framework import serializers
from stores.models.review_mod import StoreReview


class StoreReviewSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = StoreReview
        fields = [
            'id',
            'store',
            'store_name',
            'customer_email',
            'customer_name',
            'order',
            'rating',
            'comment',
            'is_verified_purchase',
            'vendor_reply',
            'vendor_replied_at',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'store',
            'store_name',
            'customer_email',
            'customer_name',
            'order',
            'is_verified_purchase',
            'vendor_reply',
            'vendor_replied_at',
            'created_at',
        ]

    def get_customer_name(self, obj):
        profile = getattr(obj.customer, 'profile', None)
        if profile and profile.full_name:
            return profile.full_name
        return obj.customer.email.split('@')[0]


class StoreReviewCreateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=True)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=True)
    comment = serializers.CharField(required=False, allow_blank=True, default='')


class StoreReviewReplySerializer(serializers.Serializer):
    reply = serializers.CharField(required=True, min_length=1, max_length=1000)
