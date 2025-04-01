from rest_framework import serializers

from stock_change.models import StockChange


class StockChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockChange
        fields = '__all__'