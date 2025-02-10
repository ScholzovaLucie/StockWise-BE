from rest_framework import viewsets

from chat_log.models import ChatLog
from chat_log.serializers import ChatLogSerializer


# Create your views here.
class ChatLogViewSet(viewsets.ModelViewSet):
    queryset = ChatLog.objects.all()
    serializer_class = ChatLogSerializer

