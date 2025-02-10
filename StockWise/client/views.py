from rest_framework import viewsets

from client.models import Client
from client.serializers import ClientSerializer


# Create your views here.
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
