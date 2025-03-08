from rest_framework import serializers

from warehouse.models import Warehouse


class WarehouseSerializer(serializers.ModelSerializer):
    positions = serializers.SerializerMethodField()

    class Meta:
        model = Warehouse
        read_only_fields = ("id",  "positions")
        fields = [
            "id",
            "name",
            "city",
            "state",
            "address",
            "psc",
            "positions"
        ]

    def get_positions(self, obj):
        positions = obj.position_set.all()
        return {
            "count": len(positions),
            "search": ",".join(positions.values_list("code", flat=True)),
        }