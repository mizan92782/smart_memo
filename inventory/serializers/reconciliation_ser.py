from decimal import Decimal
from rest_framework import serializers
from inventory.models.reconciliation_mod import (
    StockReconciliation,
    StockReconciliationItem,
    ReconciliationStatus
)


class StockReconciliationItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = StockReconciliationItem
        fields = [
            'id',
            'product',
            'product_name',
            'system_stock',
            'physical_stock',
            'discrepancy',
            'unit_cost_snapshot',
            'variance_value',
            'notes',
            'created_at',
        ]


class StockReconciliationSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    initiated_by_email = serializers.EmailField(source='initiated_by.email', read_only=True)
    applied_by_email = serializers.EmailField(source='applied_by.email', read_only=True)
    items = StockReconciliationItemSerializer(many=True, read_only=True)

    class Meta:
        model = StockReconciliation
        fields = [
            'id',
            'store',
            'store_name',
            'reconciliation_number',
            'status',
            'notes',
            'total_items_counted',
            'total_discrepancy_qty',
            'total_discrepancy_value',
            'applied_at',
            'applied_by_email',
            'initiated_by_email',
            'items',
            'created_at',
            'updated_at',
        ]


class ReconciliationItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    physical_stock = serializers.DecimalField(max_digits=10, decimal_places=3, required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class StockReconciliationCreateSerializer(serializers.Serializer):
    store_id = serializers.IntegerField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    items = ReconciliationItemInputSerializer(many=True, required=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one product item count is required.")
        return value
