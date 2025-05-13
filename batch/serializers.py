from rest_framework import serializers

from batch.models import Batch
from product.models import Product


class BatchSerializer(serializers.ModelSerializer):
    # Pole pro zadání ID produktu (PrimaryKey), mapuje se na `product`
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product"
    )
    # Pouze pro čtení – získává název produktu
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        read_only_fields = ("product_name",)
        fields = ["id", "product_id", "batch_number", "expiration_date", "product_name"]

    # Vrací název produktu pro pole `product_name`
    def get_product_name(self, obj):
        return obj.product.name

    # Podpora hromadného vytváření, pokud je vstupem list
    def create(self, validated_data):
        print(validated_data)  # Debugging

        if isinstance(validated_data, list):
            return Batch.objects.bulk_create([Batch(**batch) for batch in validated_data])

        return super().create(validated_data)


class BatchBulkSerializer(serializers.ModelSerializer):
    # Používá se pro čistě hromadné vytváření šarží
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product"
    )

    class Meta:
        model = Batch
        fields = ["product_id", "batch_number", "expiration_date"]

    # Vytvoří více záznamů najednou pomocí `bulk_create`
    def create(self, validated_data):
        return Batch.objects.bulk_create([Batch(**item) for item in validated_data])