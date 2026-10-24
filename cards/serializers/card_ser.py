"""
cards/serializers/card_ser.py — DRF Serializer for Card
"""
from rest_framework import serializers
from cards.models.card_mod import Card, CardItem
from products.serializers.product_ser import ProductSerializer


class CardItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    aisle = serializers.CharField(source='product.aisle', read_only=True, default="")
    shelf_location = serializers.CharField(source='product.shelf_location', read_only=True, default="")

    class Meta:
        model = CardItem
        fields = ['id', 'product', 'product_id', 'quantity', 'unit_price', 'subtotal', 'is_picked', 'picked_at', 'aisle', 'shelf_location']


class CardSerializer(serializers.ModelSerializer):
    items = CardItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    vendor_email = serializers.EmailField(source='vendor.email', read_only=True, default=None)
    coupon_code = serializers.CharField(source='coupon.code', read_only=True, default=None)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    estimated_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_items_count = serializers.IntegerField(read_only=True)
    picked_items_count = serializers.IntegerField(read_only=True)
    is_fully_picked = serializers.BooleanField(read_only=True)
    picking_progress_percent = serializers.FloatField(read_only=True)

    class Meta:
        model = Card
        fields = [
            'id', 'user', 'vendor', 'vendor_email', 'store', 'store_name', 'coupon', 'coupon_code',
            'title', 'shopping_mode', 'notes', 'is_completed', 'is_saved_for_later', 'planned_visit_date',
            'created_at', 'items', 'total_price', 'discount_amount', 'estimated_total',
            'total_items_count', 'picked_items_count', 'is_fully_picked', 'picking_progress_percent'
        ]
        read_only_fields = ['vendor', 'vendor_email']
