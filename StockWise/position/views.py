from rest_framework import viewsets

from position.models import Position
from position.serializers import PositionSerializer


# Create your views here.
class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
