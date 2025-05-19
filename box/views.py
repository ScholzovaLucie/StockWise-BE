from functools import reduce

from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Prefetch

from box.models import Box
from box.serializers import BoxSerializer
from group.models import Group
from utils.pagination import CustomPageNumberPagination


class BoxViewSet(viewsets.ModelViewSet):
    """
    BoxViewSet poskytuje REST API pro správu krabic (Box model).

    Funkcionalita zahrnuje:
    - standardní CRUD operace nad krabicemi (`ModelViewSet`)
    - optimalizovaný queryset přes `prefetch_related` pro načítání ID skupin v krabici
    - vlastní akci `/search/`, která umožňuje fulltextové hledání podle EAN kódu nebo kódu pozice. Podporuje vícenásobné výrazy oddělené čárkou a hledá pomocí OR kombinací.
    - vlastní akci `/products/`, která vrací seznam produktů (skupin) uložených v dané krabici. Výstup obsahuje informace o produktu, jeho názvu, množství a přiřazené skupině.

    View zároveň používá ochranu proti neplatnému dotazu (`query required`) a kontroluje existenci záznamů přes `get_object_or_404`.
    """
    queryset = Box.objects.all()
    serializer_class = BoxSerializer
    pagination_class = CustomPageNumberPagination

    @swagger_auto_schema(
        operation_description="Vrací seznam všech boxů s možností stránkování.",
        responses={200: BoxSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vytvoří nový box.",
        responses={201: BoxSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vrací detail konkrétního boxu podle ID.",
        responses={200: BoxSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Upraví celý box (PUT).",
        responses={200: BoxSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Částečně upraví box (PATCH).",
        responses={200: BoxSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Smaže box podle ID.",
        responses={204: "No Content"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        """
        Načítá boxy s přednačtením ID skupin (pro optimalizaci)
        """
        return Box.objects.prefetch_related(
            Prefetch('groups', queryset=Group.objects.only('id'))
        )

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'q', openapi.IN_QUERY,
                description="Hledaný výraz (EAN nebo kód pozice). Lze zadat více výrazů oddělených čárkou.",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'page_size', openapi.IN_QUERY,
                description="Počet položek na stránku (volitelné)",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={200: BoxSerializer(many=True)},
        operation_description="Vyhledávání boxů podle EAN nebo kódu pozice."
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Vyhledávání boxů podle EAN nebo kódu pozice
        """
        query = request.GET.get('q', '')

        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        data_query = query.split(',')
        if len(data_query) > 1:
            data_query = [term.strip() for term in data_query if term.strip()]

            query_filters = reduce(
                lambda q, term: q |
                                Q(ean__icontains=term) |
                                Q(position__code__icontains=term),
                data_query,
                Q()
            )
            boxes = Box.objects.filter(query_filters).distinct("id")
        else:
            boxes = Box.objects.filter(
                Q(ean__icontains=query) |
                Q(position__code__icontains=query)
            )

        paginator = CustomPageNumberPagination()
        paginator.page_size = request.GET.get('page_size') or 10
        paginated_data = paginator.paginate_queryset(boxes, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Seznam produktů ve skupinách uvnitř boxu",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_OBJECT)
                )
            )
        },
        operation_description="Vrací seznam produktů (ze skupin) v konkrétní krabici."
    )
    @action(detail=True, methods=['get'], url_path='products')
    def get_products_in_box(self, request, pk=None):
        """
        Vrací produkty (skupiny) obsažené v konkrétní krabici
        """
        box = get_object_or_404(Box, id=pk)
        groups = Group.objects.filter(box=box)

        product_summary = {}
        for group in groups:
            product = group.batch.product
            product_summary[group.id] = {
                "id": product.id,
                "group_id": group.id,
                "name": product.name,
                "quantity": group.quantity,
            }

        return Response(list(product_summary.values()), status=200)