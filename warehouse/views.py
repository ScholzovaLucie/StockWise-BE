from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets

from warehouse.models import Warehouse
from warehouse.serializers import WarehouseSerializer


class WarehouseViewSet(viewsets.ModelViewSet):
    """
       ViewSet pro správu skladů. Umožňuje provádět CRUD operace nad modely skladů.
       """
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer

    @swagger_auto_schema(
        operation_description="Vrací seznam všech skladů.",
        responses={200: WarehouseSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vytvoří nový sklad.",
        responses={201: WarehouseSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vrací detail skladu podle ID.",
        responses={200: WarehouseSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Upraví celý sklad (PUT).",
        responses={200: WarehouseSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Částečně upraví sklad (PATCH).",
        responses={200: WarehouseSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Smaže sklad podle ID.",
        responses={204: "No Content"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
