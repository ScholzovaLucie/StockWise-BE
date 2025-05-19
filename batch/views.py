from functools import reduce

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from batch.models import Batch
from batch.serializers import BatchSerializer
from utils.pagination import CustomPageNumberPagination


class BatchViewSet(viewsets.ModelViewSet):
    """
    BatchViewSet poskytuje REST API pro správu šarží produktů (Batch model).

    Zahrnuje:
    - standardní CRUD operace děděné z `ModelViewSet`
    - omezení záznamů dle klienta přihlášeného uživatele (`get_queryset`)
    - vlastní endpoint `/search/`, který umožňuje hledat šarže podle názvu produktu, SKU, čísla šarže nebo data expirace. Vyhledávání podporuje vícenásobné výrazy oddělené čárkou a funguje jako OR kombinace mezi jednotlivými poli a výrazy.

    Bezpečnostní filtr: Šarže jsou filtrovány podle klientů, ke kterým má přihlášený uživatel přiřazený přístup.
    """
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    pagination_class = CustomPageNumberPagination

    @swagger_auto_schema(
        operation_description="Vrací seznam všech šarží s možností filtrování dle klienta.",
        responses={200: BatchSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vytvoří novou šarži.",
        responses={201: BatchSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vrací detail šarže podle ID.",
        responses={200: BatchSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Upraví celou šarži (PUT).",
        responses={200: BatchSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Částečně upraví šarži (PATCH).",
        responses={200: BatchSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Smaže šarži podle ID.",
        responses={204: "No Content"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        """
        Vrací šarže omezené na klienty, ke kterým má uživatel přístup
        """
        queryset = Batch.objects.all()
        client_id = self.request.GET.get('client_id')
        client_ids = self.request.user.client.all().values_list('id', flat=True)
        queryset = queryset.filter(product__client_id__in=client_ids)
        if client_id:
            queryset = queryset.filter(product__client_id=client_id)
        return queryset

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'q', openapi.IN_QUERY, description="Vyhledávací dotaz (může obsahovat více hodnot oddělených čárkou)",
                type=openapi.TYPE_STRING, required=True
            ),
            openapi.Parameter(
                'clientId', openapi.IN_QUERY, description="ID klienta (volitelné)", type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'page_size', openapi.IN_QUERY, description="Počet položek na stránku", type=openapi.TYPE_INTEGER
            ),
        ],
        responses={200: BatchSerializer(many=True)},
        operation_description="Vyhledávání šarží podle názvu produktu, SKU, čísla šarže nebo expirace."
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Vlastní akce pro vyhledávání šarží podle dotazu
        """
        query = request.GET.get('q', '')
        client_id = request.GET.get('clientId', '')

        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        data_query = query.split(',')
        if len(data_query) > 1:
            data_query = [term.strip() for term in data_query if term.strip()]
            # Sestavení složeného OR dotazu přes více polí
            query_filters = reduce(
                lambda q, term: q
                                | Q(product__name__icontains=term)
                                | Q(product__sku__icontains=term)
                                | Q(batch_number__icontains=term)
                                | Q(expiration_date__icontains=term),
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
            batches = batches.filter(product__client_id=client_id)

        paginator = CustomPageNumberPagination()
        paginator.page_size = request.GET.get('page_size') or 10
        paginated_data = paginator.paginate_queryset(batches, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return paginator.get_paginated_response(serializer.data)