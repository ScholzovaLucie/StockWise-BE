from rest_framework import serializers

from box.models import Box
from position.models import Position


class BoxSerializer(serializers.ModelSerializer):
    position_id = serializers.PrimaryKeyRelatedField(
        queryset=Position.objects.all(), source="position"
    )
    groups = serializers.SerializerMethodField()
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

    def get_position(self, obj):
        return getattr(obj.position, "code", None)

    def get_groups(self, obj):
        groups = list(obj.groups.all())  # načti jen jednou
        ids = [str(group.id) for group in groups]
        return {
            "count": len(groups),
            "search": ",".join(ids),
            "title": ",".join(ids),
        }

    def create(self, validated_data):
        print(validated_data)  # Debugging

        if isinstance(validated_data, list):
            return Box.objects.bulk_create([Box(**batch) for batch in validated_data])

        return super().create(validated_data)
