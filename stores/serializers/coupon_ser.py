from decimal import Decimal
from rest_framework import serializers
from stores.models.coupon_mod import Coupon, CouponUsage, DiscountType


class CouponSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    used_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Coupon
        fields = [
            'id', 'store', 'store_name', 'code', 'discount_type',
            'discount_value', 'max_discount_amount', 'min_order_amount',
            'max_uses', 'used_count', 'max_uses_per_customer',
            'start_date', 'end_date', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'store', 'store_name', 'used_count', 'created_at', 'updated_at']

    def validate_code(self, value):
        code = str(value).strip().upper()
        if not code:
            raise serializers.ValidationError("Coupon code cannot be empty.")
        return code

    def validate_discount_value(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("Discount value must be greater than zero.")
        return value

    def validate(self, attrs):
        discount_type = attrs.get('discount_type', getattr(self.instance, 'discount_type', DiscountType.PERCENTAGE))
        discount_value = attrs.get('discount_value', getattr(self.instance, 'discount_value', Decimal('0.00')))
        if discount_type == DiscountType.PERCENTAGE and discount_value > Decimal('100.00'):
            raise serializers.ValidationError({"discount_value": "Percentage discount cannot exceed 100%."})

        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and start > end:
            raise serializers.ValidationError({"start_date": "Start date cannot be after end date."})

        return attrs


class CouponApplySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32, required=True)


class CouponUsageSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)

    class Meta:
        model = CouponUsage
        fields = [
            'id', 'coupon', 'customer', 'customer_email',
            'order', 'order_number', 'discount_applied', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
