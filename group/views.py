from functools import reduce

from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from group.models import Group
from group.serializers import GroupSerializer, GroupListSerializer
from utils.pagination import CustomPageNumberPagination


class GroupViewSet(viewsets.ModelViewSet):
    """
    GroupViewSet poskytuje REST API pro správu skupin zboží (Group model).

    Funkcionalita zahrnuje:
    - standardní CRUD operace nad skupinami (`ModelViewSet`)
    - přepnutí na zkrácený serializer při list akci pro efektivnější výstup
    - omezení záznamů dle klienta přihlášeného uživatele (`get_queryset`)
    - vlastní akci `/search/`, která umožňuje fulltextové hledání dle více atributů (ID, název produktu, SKU, číslo šarže, EAN krabice)
    - vlastní akci `/remove_from_box/`, která slouží k odebrání skupiny z krabice

    Bezpečnostní filtr: Skupiny jsou filtrovány podle klientů, ke kterým má přihlášený uživatel přiřazený přístup.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

    @swagger_auto_schema(
        operation_description="Vrací seznam všech skupin s možností filtrování dle klienta.",
        responses={200: GroupListSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vytvoří novou skupinu.",
        responses={201: GroupSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vrací detail skupiny podle ID.",
        responses={200: GroupSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Upraví celou skupinu (PUT).",
        responses={200: GroupSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Částečně upraví skupinu (PATCH).",
        responses={200: GroupSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Smaže skupinu podle ID.",
        responses={204: "No Content"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        """
        Vrací queryset omezený na klienty přihlášeného uživatele. Volitelně filtruje podle konkrétního klienta.

        :return: Queryset skupin s přednačtenými relacemi
        """
        client_id = self.request.GET.get('client_id')
        client_ids = self.request.user.client.all().values_list('id', flat=True)

        queryset = Group.objects.select_related(
            "batch__product",
            "box"
        ).prefetch_related("operations").filter(
            batch__product__client_id__in=client_ids
        )

        if client_id:
            queryset = queryset.filter(batch__product__client_id=client_id)

        return queryset

    def get_serializer_class(self):
        """
        Vrací jiný serializer při list akci (zkrácený výstup).

        :return: Serializer třída
        """
        if self.action == "list":
            return GroupListSerializer
        return GroupSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'q', openapi.IN_QUERY,
                description="Vyhledávací dotaz (může obsahovat více hodnot oddělených čárkou)",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'clientId', openapi.IN_QUERY,
                description="ID klienta (volitelné)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'page_size', openapi.IN_QUERY,
                description="Počet položek na stránku",
                type=openapi.TYPE_INTEGER
            ),
        ],
        responses={200: GroupSerializer(many=True)},
        operation_description="Vyhledávání skupin podle ID, SKU, názvu produktu, čísla šarže nebo EAN kódu krabice."
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Vyhledávání skupin podle více parametrů (id, SKU, název produktu, číslo šarže, EAN).

        :param request: HTTP GET požadavek s parametry "q" a volitelně "clientId"
        :return: JSON odpověď se serializovanými daty
        """
        query = request.GET.get('q', '')
        client_id = request.GET.get('clientId', '')

        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        data_query = query.split(',')
        if len(data_query) > 1:
            data_query = [term.strip() for term in data_query if term.strip()]
            query_filters = reduce(
                lambda q, term: q |
                                Q(id__icontains=term) |
                                Q(batch__batch_number__icontains=term) |
                                Q(batch__product__sku__icontains=term) |
                                Q(batch__product__name__icontains=term) |
                                Q(box__ean__icontains=term),
                data_query,
                Q()
            )
            groups = Group.objects.filter(query_filters).only("id")
        else:
            groups = Group.objects.filter(
                Q(id__icontains=query) |
                Q(batch__product__sku__icontains=query) |
                Q(batch__product__name__icontains=query) |
                Q(batch__batch_number__icontains=query) |
                Q(box__ean__icontains=query)
            )

        if client_id:
            groups = groups.filter(batch__product__client_id=client_id)

        paginator = CustomPageNumberPagination()
        paginator.page_size = request.GET.get('page_size') or 10
        paginated_data = paginator.paginate_queryset(groups, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_description="Odebere skupinu z krabice (resetuje i příznak přenaskenování `rescanned`).",
        responses={200: openapi.Response("Skupina úspěšně odebrána", schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ))}
    )
    @action(detail=True, methods=['post'], url_path='remove_from_box')
    def remove_from_box(self, request, pk=None):
        """
        Odebere grupu z krabice (nastaví její box na None).

        :param request: HTTP POST požadavek
        :param pk: Primární klíč grupy
        :return: JSON odpověď s potvrzením
        """
        group = get_object_or_404(Group, id=pk)

        group.box = None
        group.rescanned = False  # Resetuje příznak přenaskenování
        group.save()

        return Response({"message": f"Produkt {group.batch.product.name} odebrán z krabice."}, status=200)
