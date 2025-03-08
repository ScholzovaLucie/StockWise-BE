from functools import reduce

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from position.models import Position
from position.serializers import PositionSerializer


# Create your views here.
class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        query = request.GET.get('q', '')
        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        data_query = query.split(',')
        if len(data_query) > 1:
            data_query = [term.strip() for term in data_query if term.strip()]
            query_filters = reduce(
                lambda q, term: q |
                                Q(warehouse__name__icontains=term) |
                                Q(boxes__ean__icontains=term) |
                                Q(code__icontains=term),
                data_query,
                Q()
            )

            positions = Position.objects.filter(query_filters).distinct()

        else:
            positions = Position.objects.filter(
                Q(code__icontains=query) |
                Q(boxes__ean__icontains=query) |
                Q(warehouse__name__icontains=query)
            )

        serializer = self.get_serializer(positions, many=True)
        return Response(serializer.data)
