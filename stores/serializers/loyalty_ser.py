from rest_framework import serializers
from stores.models.loyalty_mod import (
    StoreLoyaltyProgram,
    CustomerStoreLoyalty,
    LoyaltyTransaction
)


class StoreLoyaltyProgramSerializer(serializers.ModelSerializer):
    store_name = serializers.ReadOnlyField(source='store.name')

    class Meta:
        model = StoreLoyaltyProgram
        fields = [
            'id',
            'store',
            'store_name',
            'is_active',
            'program_type',
            'points_per_currency_unit',
            'currency_per_point_redemption',
            'min_points_to_redeem',
            'stamps_for_reward',
            'stamp_reward_discount_amount',
            'min_order_for_stamp',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'store', 'store_name', 'created_at', 'updated_at']


class CustomerStoreLoyaltySerializer(serializers.ModelSerializer):
    customer_email = serializers.ReadOnlyField(source='customer.email')
    customer_name = serializers.SerializerMethodField()
    store_name = serializers.ReadOnlyField(source='store.name')

    class Meta:
        model = CustomerStoreLoyalty
        fields = [
            'id',
            'customer',
            'customer_email',
            'customer_name',
            'store',
            'store_name',
            'points_balance',
            'stamps_balance',
            'total_points_earned',
            'total_stamps_earned',
            'total_rewards_redeemed',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'customer',
            'customer_email',
            'customer_name',
            'store',
            'store_name',
            'total_points_earned',
            'total_stamps_earned',
            'total_rewards_redeemed',
            'created_at',
            'updated_at'
        ]

    def get_customer_name(self, obj) -> str:
        profile = getattr(obj.customer, 'profile', None)
        return profile.full_name if profile and profile.full_name else obj.customer.email


class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    order_number = serializers.ReadOnlyField(source='order.order_number')
    memo_number = serializers.ReadOnlyField(source='sales_memo.memo_number')

    class Meta:
        model = LoyaltyTransaction
        fields = [
            'id',
            'transaction_type',
            'points_change',
            'stamps_change',
            'points_balance_after',
            'stamps_balance_after',
            'discount_amount_applied',
            'order',
            'order_number',
            'sales_memo',
            'memo_number',
            'notes',
            'created_at'
        ]
        read_only_fields = fields
