from rest_framework import serializers
from products.models.product_mod import Product


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for the Product model."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'store',
            'store_name',
            'name',
            'second_name',
            'sku',
            'barcode',
            'aisle',
            'shelf_location',
            'description',
            'tags',
            'category',
            'category_name',
            'measure',
            'unit',
            'price',
            'currency',
            'stock',
            'in_stock',
            'is_active',
            'offer',
            'offered_discount',
            'offered_price',
            'offer_start_date',
            'offer_end_date',
            'offered_count',
            'offered_count_unit',
            'image',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'offered_price', 'created_at', 'updated_at', 'store_name', 'category_name']

    def get_in_stock(self, obj) -> bool:
        return obj.is_in_stock()
