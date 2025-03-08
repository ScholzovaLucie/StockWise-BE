from rest_framework import serializers

from batch.models import Batch
from box.serializers import BoxSerializer
from client.models import Client
from group.models import Group
from operation.models import Operation
from product.serializers import ProductSerializer


class BatchSerializer(serializers.ModelSerializer):
    product = ProductSerializer(many=False, read_only=True)

    class Meta:
        model = Batch
        ref_name = 'BatchSerializer_Operation'
        read_only_fields = ("product",)
        fields = ["id", "product", "batch_number", "expiration_date"]


class GroupSerializer(serializers.ModelSerializer):
    """Serializer pro detailní informace o skupině (group)."""
    batch = BatchSerializer(many=False, read_only=True)
    box = BoxSerializer(many=False, read_only=True)

    class Meta:
        model = Group
        ref_name = 'GroupSerializer_Operation'
        fields = ['quantity', 'batch','box']



class OperationSerializer(serializers.ModelSerializer):
    groups_amount = serializers.SerializerMethodField()
    product_amount = serializers.SerializerMethodField()
    groups_id = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        source="groups",
        many=True,
        required=False,  # Pole je volitelné
        allow_null=True  # Povolení hodnoty None
    )
    groups = GroupSerializer(many=True, read_only=True)
    groups_search = serializers.SerializerMethodField()
    product_search = serializers.SerializerMethodField()
    groups_name = serializers.SerializerMethodField()


    class Meta:
        model = Operation
        read_only_fields = (
            'id',
            "groups_amount",
            "groups_search",
            "product_search",
            'product_amount',
            'groups_name',
            'groups',
            'client_id',
            'delivery_name',
            'delivery_street',
            'delivery_city',
            'delivery_psc',
            'delivery_country',
            'delivery_phone',
            'delivery_email',
            'invoice_name',
            'invoice_street',
            'invoice_city',
            'invoice_psc',
            'invoice_country',
            'invoice_phone',
            'invoice_email',
            'invoice_ico',
            'invoice_vat'
        )

        fields = [
            'id',
            'number',
            'description',
            'type',
            'status',
            "groups_amount",
            "groups_search",
            "product_search",
            'product_amount',
            'groups_name',
            'groups_id',
            'groups',
            'client_id',
            'delivery_name',
            'delivery_street',
            'delivery_city',
            'delivery_psc',
            'delivery_country',
            'delivery_phone',
            'delivery_email',
            'invoice_name',
            'invoice_street',
            'invoice_city',
            'invoice_psc',
            'invoice_country',
            'invoice_phone',
            'invoice_email',
            'invoice_ico',
            'invoice_vat'
        ]

    def get_groups_name(self, obj):
        return ",".join([str(group) for group in obj.groups.all()])

    def get_groups_search(self, obj):
        return ",".join([str(group.id) for group in obj.groups.all()])

    def get_product_search(self, obj):
        return ",".join(obj.groups.all().values_list('batch__product__sku', flat=True))

    def get_groups_amount(self, obj):
        return obj.groups.count()

    def get_product_amount(self, obj):
        return sum([group.quantity for group in obj.groups.all()])
