from rest_framework import serializers

from box.models import Box
from position.models import Position


class BoxSerializer(serializers.ModelSerializer):
    """
    Serializer pro práci s boxy (vytváření, zobrazení detailů).

    Atributy:
        - position_id: ID pozice, ke které je box přiřazen (vstup)
        - ean: Kód EAN boxu
        - width, height, depth, weight: Rozměry a hmotnost
        - groups: Přehled skupin v boxu (pouze pro čtení)
        - position: Kód pozice, ke které box náleží (pouze pro čtení)
    """

    # ID pozice (vstup), mapuje se na objekt `position`
    position_id = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.all(), source="position"
    )

    # Vrací informace o skupinách v boxu (pouze pro čtení)
    groups = serializers.SerializerMethodField()

    # Vrací čitelný kód pozice
    position = serializers.SerializerMethodField()

    class Meta:
        model = Box
        read_only_fields = ("groups",)
        fields = [
            'id',
            'position_id',
            'ean',
            'width',
            'height',
            'depth',
            'weight',
            'groups',
            'position',
        ]

    # Vrátí kód pozice (např. A1)
    def get_position(self, obj):
        return getattr(obj.position, "code", None)

    # Vrátí přehled skupin v boxu (počet a jejich ID)
    def get_groups(self, obj):
        groups = list(obj.groups.all())  # načte jednou, pokud není předfetchováno
        ids = [str(group.id) for group in groups]
        return {
            "count": len(groups),
            "search": ",".join(ids),
            "title": ",".join(ids),
        }

    # Podpora hromadného vytváření boxů, pokud přijde list
    def create(self, validated_data):
        print(validated_data)  # Debugging

        if isinstance(validated_data, list):
            return Box.objects.bulk_create([Box(**batch) for batch in validated_data])

        return super().create(validated_data)