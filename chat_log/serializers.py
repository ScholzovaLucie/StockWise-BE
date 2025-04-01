from rest_framework import serializers

from chat_log.models import ChatLog


class ChatLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatLog
        fields = '__all__'