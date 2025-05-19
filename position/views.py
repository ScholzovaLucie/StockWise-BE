from functools import reduce

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from position.models import Position
from position.serializers import PositionSerializer
from utils.pagination import CustomPageNumberPagination


class PositionViewSet(viewsets.ModelViewSet):
    """
   ViewSet pro správu pozic (Position). Obsahuje CRUD operace a fulltextové vyhledávání.

   - Umožňuje vyhledávat podle názvu skladu, EAN krabice nebo kódu pozice.
   - Výsledky jsou stránkované pomocí `CustomPageNumberPagination`.
   """
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    pagination_class = CustomPageNumberPagination

    @swagger_auto_schema(
        operation_description="Vrací seznam všech pozic.",
        responses={200: PositionSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vrací detail pozice podle ID.",
        responses={200: PositionSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vytvoří novou pozici.",
        responses={201: PositionSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Upraví celou pozici (PUT).",
        responses={200: PositionSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Částečně upraví pozici (PATCH).",
        responses={200: PositionSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Smaže pozici podle ID.",
        responses={204: "No Content"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        method='get',
        operation_description="Vyhledává pozice podle zadaného dotazu (kód, EAN krabice, název skladu). "
                              "Podporuje vícenásobné výrazy oddělené čárkami.",
        manual_parameters=[
            openapi.Parameter('q', openapi.IN_QUERY, description="Vyhledávací dotaz (čárkami oddělené výrazy)",
                              type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Počet výsledků na stránku",
                              type=openapi.TYPE_INTEGER),
        ],
        responses={200: PositionSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Vyhledávání pozic podle zadaného dotazu `q`. Vyhledává v názvu skladu, EAN krabice a kódu pozice.

        :param request: HTTP GET požadavek s parametrem `q` (řetězec nebo čárkami oddělený seznam výrazů)
                        Nepovinně může obsahovat `page_size` pro stránkování výsledků.
        :return: Stránkovaná JSON odpověď se seznamem pozic (Position) odpovídajících dotazu.
        """
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

            positions = Position.objects.filter(query_filters).only("id")

        else:
            positions = Position.objects.filter(
                Q(code__icontains=query) |
                Q(boxes__ean__icontains=query) |
                Q(warehouse__name__icontains=query)
            )

        paginator = CustomPageNumberPagination()
        paginator.page_size = request.GET.get('page_size') or 10
        paginated_data = paginator.paginate_queryset(positions, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return paginator.get_paginated_response(serializer.data)
