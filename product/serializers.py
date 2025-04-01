from rest_framework import serializers

from batch.models import Batch
from client.models import Client
from group.models import Group
from product.models import Product


class ProductSerializer(serializers.ModelSerializer):
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), source="client"
    )
    batches = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()

    class Meta:
        model = Product
        read_only_fields = ("amount", "batches", "groups")
        fields = ["id", "client_id", "name", "sku", "description", "amount", "batches", "groups", 'created_at']

    def get_groups(self, obj):
        groups = Group.objects.filter(batch__product=obj)
        return {
            'count': len(groups),
            'search': ",".join([str(group.batch.product.sku) for group in groups]),
            'title': ",".join([str(group) for group in groups]),
        }

    def get_batches(self, obj):
        batches = obj.batches.filter(product=obj)
        return {
            'count': len(batches),
            'search': ",".join(batches.values_list("batch_number", flat=True)),
        }


    def create(self, validated_data):
        print(validated_data)  # Debugging

        if isinstance(validated_data, list):
            return Product.objects.bulk_create([Product(**item) for item in validated_data])

        return super().create(validated_data)

class ProductBulkSerializer(serializers.ModelSerializer):
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), source="client"
    )

    class Meta:
        model = Product
        fields = ["client_id", "name", "sku", "description"]

    def create(self, validated_data):
        return Product.objects.bulk_create([Product(**item) for item in validated_data])