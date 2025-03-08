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
        if obj.position:
            return obj.position.code
        return None


    def get_groups(self, obj):
        groups = obj.groups.all()
        return {
            "count": len(groups),
            "search": ",".join([str(group.id) for group in obj.groups.all()]),
            "title": ",".join([str(group) for group in obj.groups.all()]),
        }

    def create(self, validated_data):
        print(validated_data)  # Debugging

        if isinstance(validated_data, list):
            return Box.objects.bulk_create([Box(**batch) for batch in validated_data])

        return super().create(validated_data)
