from django.db.models import Sum
from rest_framework import serializers

from group.models import Group
from position.models import Position
from warehouse.models import Warehouse


class PositionSerializer(serializers.ModelSerializer):
    boxes = serializers.SerializerMethodField()
    warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(), source="warehouse"
    )
    warehouse_name = serializers.SerializerMethodField()

    class Meta:
        model = Position
        read_only_fields = ("boxes", 'warehouse_name')
        fields = ['id', 'code', 'boxes', 'warehouse_id', 'warehouse_name']

    def get_boxes(self, obj):
        boxes = obj.boxes.all()
        return {
            "count": len(boxes),
            "search": ",".join(boxes.values_list("ean", flat=True)),
        }

    def get_warehouse_name(self, obj):
        return obj.warehouse.name


class PositionBulkSerializer(serializers.ModelSerializer):
    warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(), source="warehouse"
    )

    class Meta:
        model = Position
        fields = ['code', 'warehouse_id']

    def create(self, validated_data):
        return Position.objects.bulk_create([Position(**item) for item in validated_data])