from rest_framework import serializers
from orders.models.order_mod import Order, OrderItem, SalesMemo


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name_snapshot',
            'unit_price_snapshot', 'quantity', 'line_total'
        ]


class SalesMemoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesMemo
        fields = [
            'id', 'memo_number', 'store_name_snapshot',
            'customer_email_snapshot', 'items_snapshot', 'subtotal',
            'coupon_code', 'discount_amount',
            'delivery_fee', 'total_amount', 'amount_paid', 'created_at'
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    sales_memo = SalesMemoSerializer(read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_email',
            'store', 'store_name', 'status', 'fulfillment_type',
            'delivery_address', 'delivery_fee', 'subtotal',
            'coupon_code', 'discount_amount',
            'total_amount', 'payment_method', 'payment_status',
            'idempotency_key', 'notes', 'accepted_at',
            'preparing_at', 'dispatched_at',
            'completed_at', 'cancelled_at', 'paid_at',
            'payment_collected_by', 'customer_phone_snapshot',
            'delivery_person_name', 'delivery_person_phone',
            'delivery_vehicle_type', 'delivery_tracking_notes',
            'delivery_assigned_at', 'estimated_delivery_time',
            'items', 'sales_memo', 'created_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'customer', 'customer_email',
            'store_name', 'status', 'delivery_fee', 'subtotal',
            'coupon_code', 'discount_amount',
            'total_amount', 'payment_status', 'accepted_at',
            'preparing_at', 'dispatched_at',
            'completed_at', 'cancelled_at', 'paid_at',
            'payment_collected_by', 'customer_phone_snapshot',
            'delivery_person_name', 'delivery_person_phone',
            'delivery_vehicle_type', 'delivery_tracking_notes',
            'delivery_assigned_at', 'estimated_delivery_time',
            'items', 'sales_memo', 'created_at'
        ]



class OrderSubmitSerializer(serializers.Serializer):
    card_id = serializers.IntegerField()
    fulfillment_type = serializers.ChoiceField(choices=['pickup', 'delivery'], default='pickup')
    delivery_address = serializers.CharField(required=False, default="")
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default=None)
    notes = serializers.CharField(required=False, default="")


class DeliveryAssignmentSerializer(serializers.Serializer):
    driver_name = serializers.CharField(max_length=100, required=True)
    driver_phone = serializers.CharField(max_length=30, required=True)
    vehicle_type = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    tracking_notes = serializers.CharField(required=False, allow_blank=True, default="")
    estimated_delivery_time = serializers.DateTimeField(required=False, allow_null=True, default=None)
    auto_dispatch = serializers.BooleanField(required=False, default=False)

    def validate_driver_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Driver name cannot be empty.")
        return name

    def validate_driver_phone(self, value):
        phone = value.strip()
        if not phone:
            raise serializers.ValidationError("Driver phone cannot be empty.")
        return phone
