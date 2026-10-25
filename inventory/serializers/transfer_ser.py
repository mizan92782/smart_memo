from decimal import Decimal
from rest_framework import serializers
from inventory.models.transfer_mod import StockTransfer, StockTransferItem, TransferStatus
from shared.base.base_serializer import BaseModelSerializer


class StockTransferItemSerializer(BaseModelSerializer):
    source_product_name = serializers.CharField(source='product_name_snapshot', read_only=True)
    destination_product_name = serializers.CharField(source='destination_product.name', read_only=True, default=None)

    class Meta:
        model = StockTransferItem
        fields = [
            'id', 'source_product', 'source_product_name',
            'destination_product', 'destination_product_name',
            'quantity', 'received_quantity'
        ]
        read_only_fields = fields


class StockTransferSerializer(BaseModelSerializer):
    items = StockTransferItemSerializer(many=True, read_only=True)
    source_store_name = serializers.CharField(source='source_store.name', read_only=True)
    destination_store_name = serializers.CharField(source='destination_store.name', read_only=True)
    vendor_email = serializers.CharField(source='vendor.email', read_only=True)
    waybill_slip = serializers.SerializerMethodField()

    class Meta:
        model = StockTransfer
        fields = [
            'id', 'transfer_number', 'vendor', 'vendor_email',
            'source_store', 'source_store_name',
            'destination_store', 'destination_store_name',
            'status', 'driver_name', 'driver_phone', 'vehicle_type',
            'tracking_notes', 'dispatched_at', 'received_at', 'received_by',
            'items', 'total_quantity', 'waybill_slip', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_waybill_slip(self, obj) -> str:
        return obj.format_waybill_thermal()


class StockTransferItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, required=True, min_value=Decimal('0.001'))


class StockTransferCreateSerializer(serializers.Serializer):
    source_store_id = serializers.IntegerField(required=True)
    destination_store_id = serializers.IntegerField(required=True)
    items = StockTransferItemInputSerializer(many=True, required=True)
    tracking_notes = serializers.CharField(required=False, allow_blank=True, default='')
    driver_name = serializers.CharField(required=False, allow_blank=True, default='')
    driver_phone = serializers.CharField(required=False, allow_blank=True, default='')
    vehicle_type = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one product item must be specified.")
        return value

    def validate(self, attrs):
        if attrs.get('source_store_id') == attrs.get('destination_store_id'):
            raise serializers.ValidationError("Source store and destination store cannot be the same.")
        return attrs


class StockTransferReceiveItemInputSerializer(serializers.Serializer):
    transfer_item_id = serializers.IntegerField(required=True)
    received_quantity = serializers.DecimalField(max_digits=10, decimal_places=3, required=True, min_value=Decimal('0.000'))


class StockTransferReceiveSerializer(serializers.Serializer):
    items = StockTransferReceiveItemInputSerializer(many=True, required=False, default=list)


class StockTransferCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')
