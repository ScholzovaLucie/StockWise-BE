from rest_framework import viewsets

from client_role.models import ClientRole
from client_role.serializers import ClientRoleSerializer


# Create your views here.
class ClientRoleViewSet(viewsets.ModelViewSet):
    queryset = ClientRole.objects.all()
    serializer_class = ClientRoleSerializer
