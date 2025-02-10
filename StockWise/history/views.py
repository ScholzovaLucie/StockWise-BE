from rest_framework import viewsets

from history.models import History
from history.serializers import HistorySerializer


# Create your views here.
class HistoryViewSet(viewsets.ModelViewSet):
    queryset = History.objects.all()
    serializer_class = HistorySerializer
