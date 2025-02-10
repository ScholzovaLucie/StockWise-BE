from rest_framework import viewsets

from stock_change.models import StockChange
from stock_change.serializers import StockChangeSerializer


# Create your views here.
class StockChangeViewSet(viewsets.ModelViewSet):
    queryset = StockChange.objects.all()
    serializer_class = StockChangeSerializer
