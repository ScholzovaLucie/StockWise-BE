from rest_framework import serializers
from client.models import Client
from product.models import Product


class ProductSerializer(serializers.ModelSerializer):
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), source="client"
    )

    class Meta:
        model = Product
        read_only_fields = ("amount",)
        fields = ["id", "client_id", "name", "sku", "description", "amount"]

    def create(self, validated_data):
        print(validated_data)  # Debugging

        if isinstance(validated_data, list):
            return Product.objects.bulk_create([Product(**item) for item in validated_data])

        return super().create(validated_data)