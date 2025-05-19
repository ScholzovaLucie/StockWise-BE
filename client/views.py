from functools import reduce

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from client.models import Client
from client.serializers import ClientSerializer
from utils.pagination import CustomPageNumberPagination


class ClientViewSet(viewsets.ModelViewSet):
    """
    ClientViewSet poskytuje REST API pro správu klientů.

    Zahrnuje:
    - standardní CRUD operace nad klienty (`ModelViewSet`)
    - filtraci klientů podle přístupových práv přihlášeného uživatele (`get_queryset`)
    - vlastní endpoint `/search/`, který umožňuje vyhledávat klienty podle jména nebo emailu, včetně podpory vícenásobných výrazů oddělených čárkou.

    Podporuje stránkování a volitelné filtrování podle `client_id` nebo `all=true`.
    """
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    pagination_class = CustomPageNumberPagination

    @swagger_auto_schema(
        operation_description="Vrací seznam klientů přístupných uživateli.",
        responses={200: ClientSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vytvoří nového klienta.",
        responses={201: ClientSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vrací detail klienta podle ID.",
        responses={200: ClientSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Upraví klienta (PUT).",
        responses={200: ClientSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Částečně upraví klienta (PATCH).",
        responses={200: ClientSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Smaže klienta podle ID.",
        responses={204: "No Content"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        """
        Vrací queryset klientů omezený podle oprávnění uživatele nebo podle ID.

        :return: Queryset modelu Client
        """
        queryset = Client.objects.all()
        client_id = self.request.GET.get('client_id')
        user_clients = self.request.user.client.all().values_list('id', flat=True)
        if not self.request.GET.get('all') or self.request.GET.get('all') != 'true':
            queryset = queryset.filter(id__in=user_clients)
        if client_id:
            queryset = queryset.filter(id=client_id)
        return queryset

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'q', openapi.IN_QUERY,
                description="Vyhledávací dotaz podle jména nebo emailu. Lze zadat více výrazů oddělených čárkou.",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'clientId', openapi.IN_QUERY,
                description="Filtrovat podle ID klienta (volitelné)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'page_size', openapi.IN_QUERY,
                description="Počet položek na stránku (volitelné)",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={200: ClientSerializer(many=True)},
        operation_description="Vyhledávání klientů podle jména nebo emailu."
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Vyhledávání klientů podle jména nebo emailu. Podporuje vícenásobné výrazy oddělené čárkou.

        :param request: HTTP GET požadavek s parametry 'q', 'clientId' a volitelně 'page_size'
        :return: JSON odpověď s výsledky hledání
        """
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
            clients = Client.objects.filter(query_filters).only('id')
        else:
            clients = Client.objects.filter(
                Q(name__icontains=query) | Q(email__icontains=query)
            )

        if client_id:
            clients = clients.filter(id=client_id)

        paginator = CustomPageNumberPagination()
        paginator.page_size = request.GET.get('page_size') or 10
        paginated_data = paginator.paginate_queryset(clients, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return Response(serializer.data)
