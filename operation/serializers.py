from rest_framework import serializers

from batch.models import Batch
from group.models import Group
from operation.models import Operation
from operation.services.operation_service import create_operation
from product.models import Product
from user.models import User


# --- Pomocné Mixiny a funkce ---

class GroupPrefetchMixin:
    """
    Pomocný mixin pro přístup k přednačteným grupám (`prefetched_groups`) u operací.
    """

    def _get_prefetched_groups(self, obj):
        return getattr(obj, 'prefetched_groups', obj.groups.all())


class GroupStatsMixin(GroupPrefetchMixin):
    """
    Mixin pro výpočet agregovaných statistik z grup – počet produktů, názvy, SKU apod.
    """

    def get_groups_name(self, obj):
        return ",".join(str(g) for g in self._get_prefetched_groups(obj))

    def get_groups_search(self, obj):
        return ",".join(str(g.id) for g in self._get_prefetched_groups(obj))

    def get_product_search(self, obj):
        return ",".join(
            str(g.batch.product.sku)
            for g in self._get_prefetched_groups(obj)
            if g.batch and g.batch.product
        )

    def get_groups_amount(self, obj):
        return len(self._get_prefetched_groups(obj))

    def get_product_amount(self, obj):
        return sum(g.quantity for g in self._get_prefetched_groups(obj))


def extract_delivery_data(data):
    """
    Pomocná funkce pro sestavení doručovacích údajů ze vstupních dat.
    """
    keys = [
        'delivery_name', 'delivery_street', 'delivery_city', 'delivery_psc',
        'delivery_country', 'delivery_phone', 'delivery_email'
    ]
    return {k: data.get(k) for k in keys}


def extract_invoice_data(data):
    """
    Pomocná funkce pro sestavení fakturačních údajů ze vstupních dat.
    """
    keys = [
        'invoice_name', 'invoice_street', 'invoice_city', 'invoice_psc',
        'invoice_country', 'invoice_phone', 'invoice_email', 'invoice_ico', 'invoice_vat'
    ]
    return {k: data.get(k) for k in keys}



class BatchSerializer(serializers.ModelSerializer):
    """
    Základní serializer pro šarže (Batch).
    Obsahuje pouze ID a číslo šarže.
    """

    class Meta:
        model = Batch
        fields = ["id", "batch_number"]


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer pro skupinu (Group).
    Zahrnuje množství, šarži a box.
    """

    class Meta:
        model = Group
        fields = ['quantity', 'batch', 'box']


class OperationProductSerializer(serializers.Serializer):
    """
    Serializer pro produkt v rámci operace.

    Atributy:
        - product_id: ID produktu
        - quantity: Počet kusů
        - product_name, batch_name, box_name: Zobrazovací pole (pouze pro čtení)
    """
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField()
    product_name = serializers.CharField(read_only=True)
    batch_name = serializers.CharField(required=False, allow_null=True)
    box_name = serializers.CharField(required=False, allow_null=True)


class OperationSerializer(GroupStatsMixin, serializers.ModelSerializer):
    """
    Detailní serializer pro Operation.

    Obsahuje rozšířená pole:
        - statistiky grup
        - seznam grup
        - informace o doručení a fakturaci
    """
    groups_amount = serializers.SerializerMethodField()
    product_amount = serializers.SerializerMethodField()
    groups_id = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), source="groups", many=True,
                                                   required=False)
    groups = serializers.SerializerMethodField()
    groups_search = serializers.SerializerMethodField()
    product_search = serializers.SerializerMethodField()
    groups_name = serializers.SerializerMethodField()
    delivery_data = serializers.SerializerMethodField()
    invoice_data = serializers.SerializerMethodField()

    class Meta:
        model = Operation
        fields = [
            'id', 'number', 'description', 'type', 'status',
            'groups_amount', 'groups_search', 'product_search', 'product_amount',
            'groups_name', 'groups_id', 'groups', 'client_id',
            'delivery_data', 'invoice_data', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_groups(self, obj):
        return GroupSerializer(self._get_prefetched_groups(obj), many=True).data

    def get_delivery_data(self, obj):
        return extract_delivery_data(obj.__dict__)

    def get_invoice_data(self, obj):
        return extract_invoice_data(obj.__dict__)


class OperationListSerializer(GroupStatsMixin, serializers.ModelSerializer):
    """
    Zkrácený serializer pro výpis operací (např. v seznamu).

    Zahrnuje pouze klíčová pole:
        - počet grup
        - počet produktů
        - ID grup, číslo, typ, stav, čas aktualizace
    """
    groups_amount = serializers.SerializerMethodField()
    product_amount = serializers.SerializerMethodField()
    groups_id = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), source="groups", many=True,
                                                   required=False)
    groups_search = serializers.SerializerMethodField()
    product_search = serializers.SerializerMethodField()
    groups_name = serializers.SerializerMethodField()

    class Meta:
        model = Operation
        fields = [
            'id', 'description', 'number', 'groups_id', 'type', 'status', 'updated_at',
            'groups_amount', 'groups_search', 'product_search', 'product_amount', 'groups_name'
        ]
        read_only_fields = fields


class BaseOperationCreateSerializer(serializers.Serializer):
    """
    Základní serializér pro vytvoření operace (IN nebo OUT).

    Obsahuje:
        - číslo operace, popis, stav, klienta
        - seznam produktů (vnořený serializer)
        - uživatele, který operaci vytváří
        - volitelné doručovací a fakturační údaje

    Potomek nastavuje atribut `operation_type` jako "IN" nebo "OUT".
    """
    number = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)
    status = serializers.CharField()
    client_id = serializers.IntegerField()
    products = OperationProductSerializer(many=True)
    user_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    delivery_name = serializers.CharField(required=False, allow_null=True)
    delivery_street = serializers.CharField(required=False, allow_null=True)
    delivery_city = serializers.CharField(required=False, allow_null=True)
    delivery_psc = serializers.CharField(required=False, allow_null=True)
    delivery_country = serializers.CharField(required=False, allow_null=True)
    delivery_phone = serializers.CharField(required=False, allow_null=True)
    delivery_email = serializers.EmailField(required=False, allow_null=True)

    invoice_name = serializers.CharField(required=False, allow_null=True)
    invoice_street = serializers.CharField(required=False, allow_null=True)
    invoice_city = serializers.CharField(required=False, allow_null=True)
    invoice_psc = serializers.CharField(required=False, allow_null=True)
    invoice_country = serializers.CharField(required=False, allow_null=True)
    invoice_phone = serializers.CharField(required=False, allow_null=True)
    invoice_email = serializers.EmailField(required=False, allow_null=True)
    invoice_ico = serializers.CharField(required=False, allow_null=True)
    invoice_vat = serializers.CharField(required=False, allow_null=True)

    operation_type = None  # nastaví potomek

    def create(self, validated_data):
        return create_operation(
            user=validated_data["user_id"],
            operation_type=self.operation_type,
            number=validated_data["number"],
            description=validated_data.get("description", ""),
            client_id=validated_data["client_id"],
            products=validated_data["products"],
            delivery_data=extract_delivery_data(validated_data),
            invoice_data=extract_invoice_data(validated_data)
        )


class OutOperationSerializer(BaseOperationCreateSerializer):
    """
    Serializer pro vytvoření výdejky (OUT operace).
    Dědí veškerou logiku z BaseOperationCreateSerializer.
    """
    operation_type = "OUT"


class InOperationSerializer(BaseOperationCreateSerializer):
    """
    Serializer pro vytvoření příjemky (IN operace).
    Dědí veškerou logiku z BaseOperationCreateSerializer.
    """
    operation_type = "IN"