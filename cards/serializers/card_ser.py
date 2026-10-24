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

    class Meta:
        model = CardItem
        fields = ['id', 'product', 'product_id', 'quantity', 'unit_price', 'subtotal']


class CardSerializer(serializers.ModelSerializer):
    items = CardItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    coupon_code = serializers.CharField(source='coupon.code', read_only=True, default=None)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    estimated_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Card
        fields = [
            'id', 'user', 'store', 'store_name', 'coupon', 'coupon_code',
            'title', 'shopping_mode', 'notes', 'is_completed', 'created_at', 'items',
            'total_price', 'discount_amount', 'estimated_total'
        ]
