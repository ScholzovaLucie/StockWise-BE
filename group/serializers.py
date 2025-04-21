from rest_framework import serializers

from batch.models import Batch
from box.models import Box
from group.models import Group


class GroupSerializer(serializers.ModelSerializer):
    box_id = serializers.PrimaryKeyRelatedField(
        queryset=Box.objects.all(), source="box", allow_null=True
    )
    batch_id = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(), source="batch"
    )
    name = serializers.SerializerMethodField()
    box_ean = serializers.SerializerMethodField()
    operations_in = serializers.SerializerMethodField()
    operations_out = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = Group
        ref_name = 'GroupSerializer_Group'
        read_only_fields = ("name", 'box_ean', "operations_in", "operations_out", "product_name")
        fields = ['batch_id', 'box_id', 'quantity', 'id', 'name', 'box_ean', 'operations_in', 'operations_out', "product_name", 'created_at',]

    def get_product_name(self, obj):
        if hasattr(obj, 'batch') and hasattr(obj.batch, 'product'):
            return obj.batch.product.sku
        return None

    def get_name(self, obj):
        return f"{obj.batch.product.name} ({obj.batch.batch_number})"

    def get_box_ean(self, obj):
        if obj.box:
            return obj.box.ean
        return None

    def get_operations_in(self, obj):
        operations = obj.operations.filter(type='IN')
        return {
            "count": len(operations),
            "search": ",".join(operations.values_list("number", flat=True)),
        }

    def get_operations_out(self, obj):
        operations = obj.operations.filter(type='OUT')
        return {
            "count": len(operations),
            "search": ",".join(operations.values_list("number", flat=True)),
        }

    def create(self, validated_data):
        print(validated_data)  # Debugging

        if isinstance(validated_data, list):
            return Group.objects.bulk_create([Group(**batch) for batch in validated_data])

        return super().create(validated_data)

class GroupBulkSerializer(serializers.ModelSerializer):
    box_id = serializers.PrimaryKeyRelatedField(
        queryset=Box.objects.all(), source="box", allow_null=True
    )
    batch_id = serializers.PrimaryKeyRelatedField(
        queryset=Batch.objects.all(), source="batch"
    )

    class Meta:
        model = Group
        fields = ["batch_id", "box_id", "quantity"]

    def create(self, validated_data):
        return Group.objects.bulk_create([Group(**item) for item in validated_data])


class GroupListSerializer(serializers.ModelSerializer):
    batch_id = serializers.PrimaryKeyRelatedField(read_only=True)
    box_id = serializers.PrimaryKeyRelatedField(read_only=True)
    name = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    operations_in = serializers.SerializerMethodField()
    operations_out = serializers.SerializerMethodField()

    class Meta:
        model = Group
        read_only_fields = ("operations_in", 'operations_out')
        fields = ['id', 'quantity', 'name', 'product_name', 'box_id', 'batch_id', 'operations_in', 'operations_out']

    def get_name(self, obj):
        return f"{obj.batch.product.name} ({obj.batch.batch_number})"

    def get_product_name(self, obj):
        return obj.batch.product.sku

    def get_operations_in(self, obj):
        operations = obj.operations.filter(type='IN')
        return {
            "count": len(operations),
            "search": ",".join(operations.values_list("number", flat=True)),
        }

    def get_operations_out(self, obj):
        operations = obj.operations.filter(type='OUT')
        return {
            "count": len(operations),
            "search": ",".join(operations.values_list("number", flat=True)),
        }