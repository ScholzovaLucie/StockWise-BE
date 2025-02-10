from rest_framework import viewsets

from client_user_role.models import ClientUserRole
from client_user_role.serializers import ClientUserRoleSerializer


# Create your views here.
class ClientUserRoleViewSet(viewsets.ModelViewSet):
    queryset = ClientUserRole.objects.all()
    serializer_class = ClientUserRoleSerializer
