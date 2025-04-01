from rest_framework import serializers, viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import UserDashboardConfig

class UserDashboardConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDashboardConfig
        fields = ["config"]

