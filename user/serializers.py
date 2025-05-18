from rest_framework import serializers

from client.models import Client
from user.models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer pro práci s jedním uživatelem (vytvoření, úprava).

    Atributy:
        - email: E-mail uživatele
        - password: Heslo (pouze pro zápis)
        - client_id: Seznam klientů, ke kterým má uživatel přístup (many=True)
        - name: Zobrazované jméno
    """
    password = serializers.CharField(write_only=True, required=False)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source="client",
        many=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = User
        read_only_fields = ("id",)
        fields = ["id", "email", "client_id", "password", "name"]

    def update(self, instance, validated_data):
        # Pokud je klient specifikován, nastaví se nové propojení (m2m)
        if "client" in validated_data:
            clients = validated_data.pop("client")
            instance.client.set(clients)
        return super().update(instance, validated_data)


class UserBulkSerializer(serializers.ModelSerializer):
    """
    Serializer pro hromadné vytvoření uživatelů.

    Atributy:
        - email: E-mail uživatele
        - password: Heslo (pouze pro zápis, volitelné)
        - client_id: Seznam klientů
        - name: Zobrazované jméno
    """
    password = serializers.CharField(write_only=True, required=False)
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source="client",
        many=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = User
        fields = ["email", "client_id", "password", "name"]

    def create(self, validated_data):
        # Hromadné vytvoření uživatelů včetně nastavení hesla
        users = []
        for item in validated_data:
            password = item.pop('password', None)
            user = User(**item)
            if password:
                user.set_password(password)
            users.append(user)
        return User.objects.bulk_create(users)