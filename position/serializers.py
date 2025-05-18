from django.db.models import Sum
from rest_framework import serializers

from group.models import Group
from position.models import Position
from warehouse.models import Warehouse


class PositionSerializer(serializers.ModelSerializer):
    """
    Serializer pro jednotlivou pozici ve skladu.

    Atributy:
        - code: Kód pozice (např. A01)
        - warehouse_id: ID skladu, ke kterému pozice patří (vstup)
        - warehouse_name: Název skladu (pouze pro čtení)
        - boxes: Informace o boxech na pozici – počet a jejich EANy (pouze pro čtení)
    """
    boxes = serializers.SerializerMethodField()  # Vrací seznam boxů s EANy
    warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(), source="warehouse"  # Mapuje se na relaci
    )
    warehouse_name = serializers.SerializerMethodField()  # Vrací čitelný název skladu

    class Meta:
        model = Position
        read_only_fields = ("boxes", 'warehouse_name')
        fields = ['id', 'code', 'boxes', 'warehouse_id', 'warehouse_name']

    def get_boxes(self, obj):
        # Vrací počet boxů a seznam jejich EANů pro snadné dohledání
        boxes = obj.boxes.all()
        return {
            "count": len(boxes),
            "search": ",".join(boxes.values_list("ean", flat=True)),
        }

    def get_warehouse_name(self, obj):
        # Vrací název skladu, ke kterému pozice náleží
        return obj.warehouse.name


class PositionBulkSerializer(serializers.ModelSerializer):
    """
    Serializer pro hromadné vytváření pozic.

    Atributy:
        - code: Kód pozice
        - warehouse_id: ID skladu, ke kterému pozice patří
    """
    warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(), source="warehouse"
    )

    class Meta:
        model = Position
        fields = ['code', 'warehouse_id']

    def create(self, validated_data):
        # Vytvoří více pozic najednou
        return Position.objects.bulk_create([Position(**item) for item in validated_data])