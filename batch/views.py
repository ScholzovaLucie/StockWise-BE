from functools import reduce

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.db.models import Q

from batch.models import Batch
from batch.serializers import BatchSerializer


class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer

    def get_queryset(self):
        queryset = Batch.objects.all()
        client_id = self.request.GET.get('client_id')
        client_ids = self.request.user.client.all().values_list('id', flat=True)
        queryset = queryset.filter(product__client_id__in=client_ids)
        if client_id:
            queryset = queryset.filter(product__client_id=client_id)
        return queryset

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        query = request.GET.get('q', '')
        client_id = request.GET.get('clientId', '')

        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        data_query = query.split(',')
        if len(data_query) > 1:
            data_query = [term.strip() for term in data_query if term.strip()]
            query_filters = reduce(
                lambda q, term: q
                                | Q(product__name__icontains=term)
                                | Q(product__sku__icontains=term)
                                | Q( batch_number__icontains=term)
                                | Q( expiration_date__icontains=term),
                data_query,
                Q()
            )

            batches = Batch.objects.filter(query_filters).distinct()

        else:
            batches = Batch.objects.filter(
                Q(product__name__icontains=query) |
                Q(product__sku__icontains=query) |
                Q(batch_number__icontains=query) |
                Q(expiration_date__icontains=query)
            )

        if client_id:
            batches = batches.filter(item__client_id=client_id)

        paginator = PageNumberPagination()
        paginator.page_size = request.GET.get('page_size') or 10
        paginated_data = paginator.paginate_queryset(batches, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return Response(serializer.data)