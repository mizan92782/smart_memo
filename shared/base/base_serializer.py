"""
Shared Base Serializers — Base serializer classes for common patterns.
"""
from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    """
    Base serializer that automatically includes created_at and updated_at.
    Extend this for any model serializer that needs timestamps.
    """
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.

    Usage:
        serializer = MySerializer(instance, fields=['id', 'name'])
    """

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)
        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class WriteOnlyFieldsMixin:
    """
    Mixin that makes specified fields write-only (hidden in responses).
    Usage: Define write_only_fields = ['password'] in Meta.
    """

    def get_fields(self):
        fields = super().get_fields()
        write_only = getattr(self.Meta, 'write_only_fields', [])
        for field_name in write_only:
            if field_name in fields:
                fields[field_name].write_only = True
        return fields
