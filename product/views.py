from functools import reduce
from itertools import chain

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum, Prefetch

from batch.models import Batch
from group.models import Group
from product.models import Product
from product.serializers import ProductSerializer
from utils.pagination import CustomPageNumberPagination


class ProductViewSet(viewsets.ModelViewSet):
    """
    ProductViewSet poskytuje REST API pro správu produktů.

    Funkce zahrnují:
    - standardní CRUD operace (list, retrieve, create, update, destroy)
    - filtrování podle klienta aktuálního uživatele
    - vyhledávání produktů podle názvu, popisu nebo SKU
    - hromadné vytvoření produktů (bulk_create)
    - zjištění aktuálních zásob produktu
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = CustomPageNumberPagination

    @swagger_auto_schema(
        operation_description="Vrací seznam všech produktů s možností filtrování dle klienta.",
        responses={200: ProductSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vrací detail produktu podle ID.",
        responses={200: ProductSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vytvoří nový produkt.",
        responses={201: ProductSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Upraví celý produkt (PUT).",
        responses={200: ProductSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Částečně upraví produkt (PATCH).",
        responses={200: ProductSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Smaže produkt podle ID.",
        responses={204: "No Content"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        """
        Vrací queryset produktů omezený na klienty aktuálního uživatele, s přednačtenými šaržemi a grupami.

        :return: Prefetchovaný queryset produktů.
        """
        client_id = self.request.GET.get('client_id')
        client_ids = self.request.user.client.values_list('id', flat=True)

        queryset = Product.objects.filter(client_id__in=client_ids)

        if client_id:
            queryset = queryset.filter(client_id=client_id)

        return queryset.prefetch_related(
            Prefetch('batches', queryset=Batch.objects.only('id', 'product', 'batch_number')),
            Prefetch('batches__groups', queryset=Group.objects.only('id', 'batch'))
        )

    @swagger_auto_schema(
        responses={200: ProductSerializer(many=True)},
        operation_description="Vrací seznam produktů daného klienta."
    )
    @action(detail=False, methods=['get'], url_path='by-client/(?P<client_id>[^/.]+)')
    def get_products_by_client(self, request, client_id=None):
        """
        Vrací seznam produktů patřících zadanému klientovi.

        :param request: HTTP GET požadavek
        :param client_id: ID klienta (string)
        :return: JSON odpověď se seznamem produktů
        """
        queryset = self.get_queryset().filter(client_id=client_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=ProductSerializer(many=True),
        responses={201: ProductSerializer(many=True)},
        operation_description="Vytvoří více produktů najednou (bulk insert)."
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Vytvoří více produktů najednou (bulk insert).

        :param request: HTTP POST s daty produktu nebo seznamem produktů
        :return: JSON odpověď s vytvořenými produkty
        """
        is_many = isinstance(request.data, list)
        serializer = ProductSerializer(data=request.data, many=is_many)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if is_many:
            products = Product.objects.bulk_create([Product(**item) for item in serializer.validated_data])
            return Response(ProductSerializer(products, many=True).data, status=status.HTTP_201_CREATED)

        product = serializer.save()
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('q', openapi.IN_QUERY, description="Hledaný výraz nebo víc výrazů oddělených čárkou",
                              type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('client_id', openapi.IN_QUERY, description="ID klienta (volitelné)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="Počet položek na stránku",
                              type=openapi.TYPE_INTEGER),
        ],
        responses={200: ProductSerializer(many=True)},
        operation_description="Vyhledávání produktů podle názvu, popisu nebo SKU."
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Vyhledávání produktů podle názvu, popisu nebo SKU. Podporuje vícenásobné výrazy oddělené čárkou.

        :param request: HTTP GET požadavek s parametry `q` (query string) a volitelně `client_id` a `page_size`
        :return: Stránkovaná odpověď se seznamem odpovídajících produktů
        """
        query = request.GET.get('q', '')
        client_id = request.GET.get('client_id', '')

        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        terms = [term.strip() for term in query.split(',') if term.strip()]
        filters = reduce(
            lambda acc, term: acc | Q(name__icontains=term) | Q(description__icontains=term) | Q(sku__icontains=term),
            terms,
            Q()
        )

        queryset = Product.objects.filter(filters)
        if client_id:
            queryset = queryset.filter(client_id=client_id)

        paginator = CustomPageNumberPagination()
        paginator.page_size = request.GET.get('page_size') or 10
        paginated = paginator.paginate_queryset(queryset, request)

        serializer = self.get_serializer(paginated, many=True)
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        responses={200: openapi.Response(description="Dostupné množství", schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'available': openapi.Schema(type=openapi.TYPE_INTEGER)}
        ))},
        operation_description="Vrací dostupné množství daného produktu."
    )
    @action(detail=True, methods=['get'], url_path='stock')
    def get_product_stock(self, request, pk=None):
        """
        Vrací dostupné množství daného produktu.

        :param request: HTTP GET požadavek
        :param pk: ID produktu
        :return: JSON odpověď s množstvím nebo chybovou hláškou
        """
        try:
            product = Product.objects.only('id', 'amount_cached').get(pk=pk)
            return Response({"available": product.amount_cached}, status=200)
        except Product.DoesNotExist:
            return Response({"error": "Produkt nebyl nalezen"}, status=404)