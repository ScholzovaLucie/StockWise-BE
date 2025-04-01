from rest_framework import serializers

from client_role.models import ClientRole


class ClientRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientRole
        fields = '__all__'