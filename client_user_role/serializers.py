from rest_framework import serializers

from client_user_role.models import ClientUserRole


class ClientUserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientUserRole
        fields = '__all__'