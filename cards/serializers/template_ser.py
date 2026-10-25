from decimal import Decimal
from rest_framework import serializers
from cards.models.template_mod import StoreMemoTemplate, StoreMemoTemplateItem


class StoreMemoTemplateItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    barcode = serializers.CharField(source='product.barcode', read_only=True, default='')
    sku = serializers.CharField(source='product.sku', read_only=True, default='')
    aisle = serializers.CharField(source='product.aisle', read_only=True, default='')
    shelf_location = serializers.CharField(source='product.shelf_location', read_only=True, default='')
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_in_stock = serializers.SerializerMethodField()
    available_stock = serializers.SerializerMethodField()

    class Meta:
        model = StoreMemoTemplateItem
        fields = [
            'id',
            'product_id',
            'product_name',
            'barcode',
            'sku',
            'aisle',
            'shelf_location',
            'quantity',
            'unit_price',
            'subtotal',
            'notes',
            'is_in_stock',
            'available_stock',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_in_stock(self, obj) -> bool:
        prod = obj.product
        if not prod or not prod.is_active or prod.is_deleted:
            return False
        balance = getattr(prod, 'stock_balance', None)
        if not balance:
            return False
        available = balance.on_hand - balance.reserved
        return available >= obj.quantity

    def get_available_stock(self, obj) -> str:
        prod = obj.product
        if not prod:
            return "0.000"
        balance = getattr(prod, 'stock_balance', None)
        if not balance:
            return "0.000"
        available = max(Decimal('0.000'), balance.on_hand - balance.reserved)
        return str(available)


class StoreMemoTemplateSerializer(serializers.ModelSerializer):
    items = StoreMemoTemplateItemSerializer(many=True, read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    vendor_email = serializers.EmailField(source='vendor.email', read_only=True, default=None)
    total_items_count = serializers.IntegerField(read_only=True)
    estimated_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = StoreMemoTemplate
        fields = [
            'id',
            'name',
            'description',
            'user',
            'store',
            'store_name',
            'vendor',
            'vendor_email',
            'shopping_mode',
            'is_favorite',
            'items',
            'total_items_count',
            'estimated_total',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'vendor', 'vendor_email', 'total_items_count', 'estimated_total', 'created_at', 'updated_at']


class TemplateItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=3, required=False, default=Decimal('1.000'))
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')


class LoadTemplateToMemoSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=['replace', 'merge'], default='replace')
    shopping_mode = serializers.ChoiceField(choices=['remote', 'walk_in'], required=False, default=None)


class SaveAsTemplateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=True)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    is_favorite = serializers.BooleanField(required=False, default=False)
