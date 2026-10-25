from rest_framework import serializers
from products.models.product_mod import Product
from products.models.product_image_mod import ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product gallery images."""
    effective_url = serializers.CharField(read_only=True)

    class Meta:
        model = ProductImage
        fields = [
            'id',
            'product',
            'image',
            'image_url',
            'effective_url',
            'is_primary',
            'display_order',
            'alt_text',
            'created_at'
        ]
        read_only_fields = ['id', 'product', 'effective_url', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for the Product model."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    in_stock = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    primary_image_url = serializers.CharField(read_only=True)

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
            'images',
            'primary_image_url',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'offered_price', 'created_at', 'updated_at', 'store_name', 'category_name', 'images', 'primary_image_url']

    def get_in_stock(self, obj) -> bool:
        return obj.is_in_stock()
