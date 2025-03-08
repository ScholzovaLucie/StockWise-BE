from rest_framework import serializers

from client.models import Client
from user.models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source="client",
        many=True,
        required=False,  # Pole je volitelné
        allow_null=True  # Povolení hodnoty None
    )

    class Meta:
        model = User
        read_only_fields = ("id",)
        fields = ["id", "email", "client_id", "password", "name"]

    def update(self, instance, validated_data):
        if "client" in validated_data:
            clients = validated_data.pop("client")
            instance.client.set(clients)
        return super().update(instance, validated_data)