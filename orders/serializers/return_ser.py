from decimal import Decimal
from rest_framework import serializers
from orders.models.return_mod import OrderReturn, OrderReturnItem, ReturnStatus, ReturnReason
from shared.base.base_serializer import BaseModelSerializer


class OrderReturnItemSerializer(BaseModelSerializer):
    product_name = serializers.CharField(source='product_name_snapshot', read_only=True)

    class Meta:
        model = OrderReturnItem
        fields = [
            'id', 'order_item', 'product', 'product_name',
            'quantity', 'unit_price', 'refund_subtotal'
        ]
        read_only_fields = fields


class OrderReturnSerializer(BaseModelSerializer):
    items = OrderReturnItemSerializer(many=True, read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    credit_note_slip = serializers.SerializerMethodField()

    class Meta:
        model = OrderReturn
        fields = [
            'id', 'return_number', 'order', 'order_number', 'store', 'store_name',
            'customer', 'customer_email', 'vendor', 'status', 'reason',
            'reason_notes', 'rejection_reason', 'total_refund_amount',
            'restock_inventory', 'processed_by', 'processed_at',
            'items', 'items_snapshot', 'loyalty_points_deducted',
            'loyalty_stamps_deducted', 'credit_note_slip', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_credit_note_slip(self, obj) -> str:
        return obj.format_credit_note_thermal()


class OrderReturnItemInputSerializer(serializers.Serializer):
    order_item_id = serializers.IntegerField(required=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, required=True, min_value=Decimal('0.001'))


class OrderReturnRequestSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=True)
    reason = serializers.ChoiceField(choices=ReturnReason.choices, default=ReturnReason.DAMAGED_DEFECTIVE)
    reason_notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = OrderReturnItemInputSerializer(many=True, required=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item must be submitted for return.")
        return value


class OrderReturnProcessSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['approved', 'rejected'], required=True)
    restock_inventory = serializers.BooleanField(default=True, required=False)
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs.get('decision') == 'rejected' and not attrs.get('rejection_reason', '').strip():
            raise serializers.ValidationError({"rejection_reason": "Rejection reason is required when rejecting a return."})
        return attrs
