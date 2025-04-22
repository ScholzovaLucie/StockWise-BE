from rest_framework import serializers

from batch.models import Batch
from box.serializers import BoxSerializer
from client.models import Client
from group.models import Group
from operation.models import Operation
from operation.services.operation_service import create_operation
from product.models import Product
from product.serializers import ProductSerializer
from user.models import User

class GroupPrefetchMixin:
    def _get_prefetched_groups(self, obj):
        return getattr(obj, 'prefetched_groups', obj.groups.all())

class GroupStatsMixin(GroupPrefetchMixin):
    def get_groups_name(self, obj):
        return ",".join(str(group) for group in self._get_prefetched_groups(obj))

    def get_groups_search(self, obj):
        return ",".join(str(group.id) for group in self._get_prefetched_groups(obj))

    def get_product_search(self, obj):
        return ",".join(
            str(group.batch.product.sku)
            for group in self._get_prefetched_groups(obj)
            if group.batch and group.batch.product
        )

    def get_groups_amount(self, obj):
        return len(self._get_prefetched_groups(obj))

    def get_product_amount(self, obj):
        return sum(group.quantity for group in self._get_prefetched_groups(obj))


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ["id", "batch_number"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['quantity', 'batch', 'box']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data



class OperationSerializer(GroupStatsMixin, serializers.ModelSerializer):
    groups_amount = serializers.SerializerMethodField()
    product_amount = serializers.SerializerMethodField()
    groups_id = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        source="groups",
        many=True,
        required=False,  # Pole je volitelné
        allow_null=True  # Povolení hodnoty None
    )
    groups = serializers.SerializerMethodField()
    groups_search = serializers.SerializerMethodField()
    product_search = serializers.SerializerMethodField()
    groups_name = serializers.SerializerMethodField()
    delivery_data = serializers.SerializerMethodField()
    invoice_data = serializers.SerializerMethodField()


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
            'delivery_data',
            'invoice_data',
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
            'delivery_data',
            'invoice_data',
            'created_at',
            'updated_at'
        ]

    def get_delivery_data(self, obj):
        return {
            'delivery_date': obj.delivery_date,
            'delivery_name': obj.delivery_name,
            'delivery_street': obj.delivery_street,
            'delivery_city': obj.delivery_city,
            'delivery_psc': obj.delivery_psc,
            'delivery_country': obj.delivery_country,
            'delivery_phone': obj.delivery_phone,
            'delivery_email': obj.delivery_email,
            'delivery_note': obj.delivery_note,
        }

    def get_invoice_data(self, obj):
        return {
            'invoice_name': obj.invoice_name,
            'invoice_street': obj.invoice_street,
            'invoice_city': obj.invoice_city,
            'invoice_psc': obj.invoice_psc,
            'invoice_country': obj.invoice_country,
            'invoice_phone': obj.invoice_phone,
            'invoice_email': obj.invoice_email,
            'invoice_ico': obj.invoice_ico,
            'invoice_vat': obj.invoice_vat,
        }

    def get_groups(self, obj):
        groups = self._get_prefetched_groups(obj)
        return GroupSerializer(groups, many=True).data


class OperationListSerializer(GroupStatsMixin, serializers.ModelSerializer):
    groups_amount = serializers.SerializerMethodField()
    product_amount = serializers.SerializerMethodField()
    groups_id = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        source="groups",
        many=True,
        required=False,
        allow_null=True
    )
    groups_search = serializers.SerializerMethodField()
    product_search = serializers.SerializerMethodField()
    groups_name = serializers.SerializerMethodField()

    class Meta:
        model = Operation
        read_only_fields = (
            'id', 'groups_id', "groups_amount", "groups_search",
            "product_search", 'product_amount', 'groups_name',
        )
        fields = [
            'id', 'description', 'number', 'groups_id', 'type', 'status', 'updated_at',
            "groups_amount", "groups_search", "product_search", 'product_amount', 'groups_name',
        ]



class OperationProductSerializer(serializers.Serializer):
    """Serializer pro produkty v operaci (výdejka / příjemka)"""
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField()
    product_name = serializers.CharField(read_only=True)
    batch_name = serializers.CharField(required=False, allow_null=True)
    box_name = serializers.CharField(required=False, allow_null=True)


class OutOperationSerializer(serializers.Serializer):
    """Serializer pro výdejku (OUT operation) s produkty a fakturačními údaji"""
    number = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)
    status = serializers.CharField()
    client_id = serializers.IntegerField()
    products = OperationProductSerializer(many=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    # Doručovací údaje
    delivery_name = serializers.CharField(required=False, allow_null=True)
    delivery_street = serializers.CharField(required=False, allow_null=True)
    delivery_city = serializers.CharField(required=False, allow_null=True)
    delivery_psc = serializers.CharField(required=False, allow_null=True)
    delivery_country = serializers.CharField(required=False, allow_null=True)
    delivery_phone = serializers.CharField(required=False, allow_null=True)
    delivery_email = serializers.EmailField(required=False, allow_null=True)

    # Fakturační údaje
    invoice_name = serializers.CharField(required=False, allow_null=True)
    invoice_street = serializers.CharField(required=False, allow_null=True)
    invoice_city = serializers.CharField(required=False, allow_null=True)
    invoice_psc = serializers.CharField(required=False, allow_null=True)
    invoice_country = serializers.CharField(required=False, allow_null=True)
    invoice_phone = serializers.CharField(required=False, allow_null=True)
    invoice_email = serializers.EmailField(required=False, allow_null=True)
    invoice_ico = serializers.CharField(required=False, allow_null=True)
    invoice_vat = serializers.CharField(required=False, allow_null=True)

    def create(self, validated_data):
        """Použití existující metody `create_operation` pro vytvoření výdejky."""
        try:
            return create_operation(
                user=validated_data["user_id"],
                operation_type="OUT",
                number=validated_data["number"],
                description=validated_data.get("description", ""),
                client_id=validated_data["client_id"],
                products=validated_data["products"],
                delivery_data={
                    'delivery_name': validated_data["delivery_name"],
                    'delivery_street': validated_data["delivery_street"],
                    'delivery_city': validated_data["delivery_city"],
                    'delivery_psc':validated_data["delivery_psc"],
                    'delivery_country': validated_data["delivery_country"],
                    'delivery_phone': validated_data["delivery_phone"],
                    'delivery_email': validated_data["delivery_email"],
                },
                invoice_data={
                    'invoice_name': validated_data["invoice_name"],
                    'invoice_street': validated_data["invoice_street"],
                    'invoice_city': validated_data["invoice_city"],
                    'invoice_psc': validated_data["invoice_psc"],
                    'invoice_country': validated_data["invoice_country"],
                    'invoice_phone': validated_data["invoice_phone"],
                    'invoice_email': validated_data["invoice_email"],
                    'invoice_ico': validated_data["invoice_ico"],
                    'invoice_vat': validated_data["invoice_vat"]
                }
            )

        except Exception as e:
            raise Exception(e)


class InOperationSerializer(serializers.Serializer):
    """Serializer pro příjemku (IN operation) s produkty"""
    number = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)
    status = serializers.CharField()
    client_id = serializers.IntegerField()
    products = OperationProductSerializer(many=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    def create(self, validated_data):
        """Použití existující metody `create_operation` pro vytvoření příjemky."""
        try:
            return create_operation(
                user=validated_data["user_id"],
                operation_type="IN",
                number=validated_data["number"],
                description=validated_data.get("description", ""),
                client_id=validated_data["client_id"],
                products=validated_data["products"]
            )
        except Exception as e:
            raise Exception(e)


class OutOperationBulkSerializer(serializers.Serializer):
    number = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)
    status = serializers.CharField()
    client_id = serializers.IntegerField()
    products = OperationProductSerializer(many=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    # Doručovací údaje
    delivery_name = serializers.CharField(required=False, allow_null=True)
    delivery_street = serializers.CharField(required=False, allow_null=True)
    delivery_city = serializers.CharField(required=False, allow_null=True)
    delivery_psc = serializers.CharField(required=False, allow_null=True)
    delivery_country = serializers.CharField(required=False, allow_null=True)
    delivery_phone = serializers.CharField(required=False, allow_null=True)
    delivery_email = serializers.EmailField(required=False, allow_null=True)

    # Fakturační údaje
    invoice_name = serializers.CharField(required=False, allow_null=True)
    invoice_street = serializers.CharField(required=False, allow_null=True)
    invoice_city = serializers.CharField(required=False, allow_null=True)
    invoice_psc = serializers.CharField(required=False, allow_null=True)
    invoice_country = serializers.CharField(required=False, allow_null=True)
    invoice_phone = serializers.CharField(required=False, allow_null=True)
    invoice_email = serializers.EmailField(required=False, allow_null=True)
    invoice_ico = serializers.CharField(required=False, allow_null=True)
    invoice_vat = serializers.CharField(required=False, allow_null=True)

    def create(self, validated_data):
        return create_operation(
            user=validated_data["user_id"],
            operation_type="OUT",
            number=validated_data["number"],
            description=validated_data.get("description", ""),
            client_id=validated_data["client_id"],
            products=validated_data["products"],
            delivery_data={
                'delivery_name': validated_data.get("delivery_name"),
                'delivery_street': validated_data.get("delivery_street"),
                'delivery_city': validated_data.get("delivery_city"),
                'delivery_psc': validated_data.get("delivery_psc"),
                'delivery_country': validated_data.get("delivery_country"),
                'delivery_phone': validated_data.get("delivery_phone"),
                'delivery_email': validated_data.get("delivery_email"),
            },
            invoice_data={
                'invoice_name': validated_data.get("invoice_name"),
                'invoice_street': validated_data.get("invoice_street"),
                'invoice_city': validated_data.get("invoice_city"),
                'invoice_psc': validated_data.get("invoice_psc"),
                'invoice_country': validated_data.get("invoice_country"),
                'invoice_phone': validated_data.get("invoice_phone"),
                'invoice_email': validated_data.get("invoice_email"),
                'invoice_ico': validated_data.get("invoice_ico"),
                'invoice_vat': validated_data.get("invoice_vat")
            }
        )


class InOperationBulkSerializer(serializers.Serializer):
    number = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)
    status = serializers.CharField()
    client_id = serializers.IntegerField()
    products = OperationProductSerializer(many=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    def create(self, validated_data):
        return create_operation(
            user=validated_data["user_id"],
            operation_type="IN",
            number=validated_data["number"],
            description=validated_data.get("description", ""),
            client_id=validated_data["client_id"],
            products=validated_data["products"]
        )
