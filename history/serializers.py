from rest_framework import serializers

import operation
import product
from batch.models import Batch
from group.models import Group
from history.models import History
from operation.models import Operation
from position.models import Position
from product.models import Product


class HistorySerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    data = serializers.SerializerMethodField()

    class Meta:
        model = History
        fields = ['id', 'type', 'description', 'timestamp', 'user_name', 'data']

    def get_user_name(self, obj):
        return obj.user.name if obj.user else None

    def get_data(self, obj):
        models_map = {
            'operation': (Operation, 'number'),
            'product': (Product, 'name'),
            'batch': (Batch, 'batch_number'),
            'group': (Group, '__str__'),
            'position': (Position, 'code'),
        }

        model_class, attr = models_map[obj.type]
        try:
            instance = model_class.objects.get(pk=obj.related_id)
        except model_class.DoesNotExist:
            return None

        if attr == '__str__':
            return str(instance)
        return getattr(instance, attr)