from rest_framework import viewsets

from box.models import Box
from box.serializers import BoxSerializer


# Create your views here.
class BoxViewSet(viewsets.ModelViewSet):
    queryset = Box.objects.all()
    serializer_class = BoxSerializer
