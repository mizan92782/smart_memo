from rest_framework import serializers


class DateRangeFilterSerializer(serializers.Serializer):
    store_id = serializers.IntegerField(required=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        start = attrs.get('start_date')
        end = attrs.get('end_date')
        if start and end and start > end:
            raise serializers.ValidationError("start_date cannot be after end_date.")
        return attrs


class StoreFilterSerializer(serializers.Serializer):
    store_id = serializers.IntegerField(required=True)
