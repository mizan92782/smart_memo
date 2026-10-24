"""
categories/serializers/category_ser.py — DRF Serializer for Category
"""
from rest_framework import serializers
from categories.models.category_mod import Category


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for the Category model."""
    product_count = serializers.IntegerField(source='products.count', read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'product_count']
