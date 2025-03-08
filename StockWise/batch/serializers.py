from rest_framework import serializers

from batch.models import Batch
from product.models import Product


class BatchSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product"
    )
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = Batch
        read_only_fields = ("product_name",)
        fields = ["id", "product_id", "batch_number", "expiration_date", 'product_name']

    def get_product_name(self, obj):
        return obj.product.name

    def create(self, validated_data):
        print(validated_data)  # Debugging

        if isinstance(validated_data, list):
            return Batch.objects.bulk_create([Batch(**batch) for batch in validated_data])

        return super().create(validated_data)