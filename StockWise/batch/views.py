from rest_framework import viewsets

from batch.models import Batch

from batch.serializers import BatchSerializer


# Create your views here.
class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
