from itertools import chain

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
        read_only_fields = ("amount_cached", "batches", "groups")
        fields = ["id", "client_id", "name", "sku", "description", "amount_cached", "batches", "groups", 'created_at']

    def get_batches(self, obj):
        batches = list(obj.batches.all())
        return {
            'count': len(batches),
            'search': ",".join(batch.batch_number for batch in batches),
        }

    def get_groups(self, obj):
        batches = obj.batches.all()
        all_groups = list(chain.from_iterable(batch.groups.all() for batch in batches))
        return {
            'count': len(all_groups),
            'search': ",".join(str(g.id) for g in all_groups),
            'title': ",".join(str(g) for g in all_groups),
        }

    def create(self, validated_data):
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