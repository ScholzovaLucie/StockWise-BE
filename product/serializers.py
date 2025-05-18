from itertools import chain

from rest_framework import serializers

from batch.models import Batch
from client.models import Client
from group.models import Group
from product.models import Product


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer pro detail produktu, včetně vazeb na šarže a skupiny.

    Atributy:
        - client_id: ID klienta (vstupní pole mapované na relaci)
        - batches: Info o šaržích produktu (pouze pro čtení)
        - groups: Info o skupinách produktu (pouze pro čtení)
        - amount_cached: Uložená hodnota počtu kusů (read-only)
    """
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), source="client"
    )
    batches = serializers.SerializerMethodField()  # Vrací přehled šarží produktu
    groups = serializers.SerializerMethodField()   # Vrací přehled skupin navázaných přes šarže

    class Meta:
        model = Product
        read_only_fields = ("amount_cached", "batches", "groups")
        fields = ["id", "client_id", "name", "sku", "description", "amount_cached", "batches", "groups", 'created_at']

    def get_batches(self, obj):
        # Vrací počet šarží a jejich názvy (batch_number) jako řetězec
        batches = list(obj.batches.all())
        return {
            'count': len(batches),
            'search': ",".join(batch.batch_number for batch in batches),
        }

    def get_groups(self, obj):
        # Načte všechny skupiny produktu skrze jeho šarže
        batches = obj.batches.all()
        all_groups = list(chain.from_iterable(batch.groups.all() for batch in batches))
        return {
            'count': len(all_groups),
            'search': ",".join(str(g.id) for g in all_groups),
            'title': ",".join(str(g) for g in all_groups),
        }

    def create(self, validated_data):
        # Podpora hromadného vytváření, pokud přijde seznam objektů
        if isinstance(validated_data, list):
            return Product.objects.bulk_create([Product(**item) for item in validated_data])
        return super().create(validated_data)


class ProductBulkSerializer(serializers.ModelSerializer):
    """
    Serializer pro hromadné vytvoření produktů.

    Atributy:
        - client_id: ID klienta
        - name, sku, description: Popis produktu
    """
    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(), source="client"
    )

    class Meta:
        model = Product
        fields = ["client_id", "name", "sku", "description"]

    def create(self, validated_data):
        # Vytvoří více produktů najednou pomocí `bulk_create`
        return Product.objects.bulk_create([Product(**item) for item in validated_data])