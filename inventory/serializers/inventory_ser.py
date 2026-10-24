from rest_framework import serializers
from inventory.models.inventory_mod import StockBalance, StockLedgerEntry


class StockBalanceSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    available = serializers.DecimalField(max_digits=10, decimal_places=3, read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = StockBalance
        fields = [
            'id', 'store', 'product', 'product_name', 'product_sku',
            'product_unit', 'on_hand', 'reserved', 'available',
            'low_stock_threshold', 'is_low_stock', 'updated_at'
        ]
        read_only_fields = ['id', 'store', 'product', 'on_hand', 'reserved', 'available', 'is_low_stock', 'updated_at']


class StockLedgerEntrySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    actor_email = serializers.EmailField(source='actor.email', read_only=True)

    class Meta:
        model = StockLedgerEntry
        fields = [
            'id', 'store', 'product', 'product_name', 'movement_type',
            'quantity', 'balance_after', 'reference_id', 'actor_email',
            'notes', 'created_at'
        ]
        read_only_fields = ['id', 'store', 'product', 'movement_type', 'quantity', 'balance_after', 'reference_id', 'actor_email', 'created_at']


class StockAdjustmentSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3)
    reason = serializers.CharField(required=False, default="manual_adjustment")
    notes = serializers.CharField(required=False, default="")
