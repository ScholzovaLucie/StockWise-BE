from rest_framework import viewsets

from group.models import Group
from group.serializers import GroupSerializer


# Create your views here.
class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
