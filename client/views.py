from functools import reduce

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from client.models import Client
from client.serializers import ClientSerializer


# Create your views here.
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer

    def get_queryset(self):
        queryset = Client.objects.all()
        client_id = self.request.GET.get('client')
        user_clients = self.request.user.client.all().values_list('id', flat=True)
        if not self.request.GET.get('all') or self.request.GET.get('all') != 'true':
            queryset = queryset.filter(id__in=user_clients)
        if client_id:
            queryset = queryset.filter(id=client_id)
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
                lambda q, term: q | Q(name__icontains=term) | Q(email__icontains=term),
                data_query,
                Q()
            )

            clients = Client.objects.filter(query_filters).distinct()

        else:
            clients = Client.objects.filter(
                Q(name__icontains=query) | Q(email__icontains=query)
            )

        if client_id:
            clients = clients.filter(id=client_id)


        serializer = self.get_serializer(clients, many=True)
        return Response(serializer.data)
