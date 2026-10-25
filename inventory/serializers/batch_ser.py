from decimal import Decimal
from rest_framework import serializers
from inventory.models.batch_mod import ProductBatch, BatchStatus
from products.models.product_mod import Product
from stores.models.store_mod import Store


class ProductBatchSerializer(serializers.ModelSerializer):
    """Read serializer for perishable product batches with dynamic computed metrics."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    product_unit = serializers.CharField(source='product.unit', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    days_until_expiry = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    clearance_unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_valuation = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ProductBatch
        fields = [
            'id',
            'store',
            'store_name',
            'product',
            'product_name',
            'product_sku',
            'product_unit',
            'batch_number',
            'manufacture_date',
            'expiry_date',
            'initial_quantity',
            'current_quantity',
            'cost_price',
            'status',
            'is_clearance',
            'clearance_discount_percent',
            'clearance_unit_price',
            'total_valuation',
            'days_until_expiry',
            'is_expired',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'current_quantity',
            'status',
            'created_at',
            'updated_at',
        ]

    def get_days_until_expiry(self, obj) -> int:
        return obj.days_until_expiry()


class ProductBatchCreateSerializer(serializers.Serializer):
    """Input serializer for registering a new batch."""
    store_id = serializers.IntegerField(required=False)
    product_id = serializers.IntegerField(required=True)
    batch_number = serializers.CharField(max_length=64, required=True)
    manufacture_date = serializers.DateField(required=False, allow_null=True)
    expiry_date = serializers.DateField(required=True)
    initial_quantity = serializers.DecimalField(max_digits=10, decimal_places=3, required=True, min_value=Decimal('0.001'))
    cost_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=Decimal('0.00'), min_value=Decimal('0.00'))
    add_to_stock = serializers.BooleanField(required=False, default=False)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class BatchDisposalSerializer(serializers.Serializer):
    """Input serializer for writing off spoiled or expired stock from a batch."""
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, allow_null=True, min_value=Decimal('0.001'))
    reason = serializers.CharField(max_length=150, required=False, default="Expired / Spoilage")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class BatchClearanceSerializer(serializers.Serializer):
    """Input serializer for applying clearance discount to a batch."""
    discount_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=True, min_value=Decimal('0.00'), max_value=Decimal('100.00'))


class FEFOAllocationSerializer(serializers.Serializer):
    """Input serializer for FEFO stock allocation."""
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, required=True, min_value=Decimal('0.001'))
    deduct = serializers.BooleanField(required=False, default=True)
