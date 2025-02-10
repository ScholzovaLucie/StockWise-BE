from rest_framework import viewsets

from warehouse.models import Warehouse
from warehouse.serializers import WarehouseSerializer


# Create your views here.
class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
