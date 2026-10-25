from decimal import Decimal
from rest_framework import serializers
from purchases.models.purchase_mod import Supplier, Purchase, PurchaseItem


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id', 'store', 'name', 'contact_person', 'email',
            'phone', 'address', 'tax_id', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PurchaseItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = PurchaseItem
        fields = [
            'id', 'product', 'product_name', 'quantity',
            'unit_cost', 'line_total'
        ]


class PurchaseItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal('0.001'))
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.00'))


class PurchaseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    items = PurchaseItemSerializer(many=True, read_only=True)

    class Meta:
        model = Purchase
        fields = [
            'id', 'purchase_number', 'store', 'store_name',
            'supplier', 'supplier_name', 'status', 'reference',
            'order_date', 'received_date', 'subtotal',
            'additional_charges', 'total_cost', 'notes',
            'items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'purchase_number', 'status', 'order_date',
            'received_date', 'subtotal', 'total_cost',
            'created_at', 'updated_at'
        ]


class PurchaseCreateSerializer(serializers.Serializer):
    store_id = serializers.IntegerField()
    supplier_id = serializers.IntegerField()
    reference = serializers.CharField(required=False, allow_blank=True, default="")
    additional_charges = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=Decimal('0.00'), min_value=Decimal('0.00')
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = PurchaseItemCreateSerializer(many=True, allow_empty=False)


class GenerateLowStockPOSerializer(serializers.Serializer):
    """Input serializer for automated low-stock purchase order generation."""
    store_id = serializers.IntegerField(required=True)
    default_supplier_id = serializers.IntegerField(required=False, allow_null=True)
    include_open_order_guard = serializers.BooleanField(required=False, default=True)
