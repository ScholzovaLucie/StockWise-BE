from rest_framework import serializers

from batch.models import Batch
from box.models import Box
from group.models import Group


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer pro detailní zobrazení a vytváření skupin.

    Atributy:
        - batch_id: ID šarže (Batch) – povinné
        - box_id: ID boxu (Box) – volitelné
        - quantity: Počet kusů ve skupině
        - name: Název složený z názvu produktu a čísla šarže (jen pro čtení)
        - box_ean: EAN boxu (jen pro čtení)
        - operations_in: Souhrn IN operací (počet, vyhledávací řetězec)
        - operations_out: Souhrn OUT operací (počet, vyhledávací řetězec)
        - product_name: SKU produktu (jen pro čtení)
    """

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
        fields = ['batch_id', 'box_id', 'quantity', 'id', 'name', 'box_ean', 'operations_in', 'operations_out', "product_name", 'created_at']

    def get_product_name(self, obj):
        return getattr(obj.batch.product, 'sku', None)

    def get_name(self, obj):
        return f"{obj.batch.product.name} ({obj.batch.batch_number})"

    def get_box_ean(self, obj):
        return obj.box.ean if obj.box else None

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
        if isinstance(validated_data, list):
            return Group.objects.bulk_create([Group(**batch) for batch in validated_data])
        return super().create(validated_data)


class GroupBulkSerializer(serializers.ModelSerializer):
    """
    Serializer pro hromadné vytvoření skupin.

    Atributy:
        - batch_id: ID šarže
        - box_id: ID boxu (volitelné)
        - quantity: Počet kusů
    """

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
    """
    Serializer pro zjednodušený výpis skupin v seznamu.

    Atributy:
        - id: ID skupiny
        - quantity: Počet kusů
        - name: Název skupiny (produkt + šarže)
        - product_name: SKU produktu
        - box_id: ID boxu (jen pro čtení)
        - batch_id: ID šarže (jen pro čtení)
        - operations_in: Souhrn IN operací
        - operations_out: Souhrn OUT operací
    """

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