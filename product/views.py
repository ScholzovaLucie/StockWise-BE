from functools import reduce
from itertools import chain

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
    ViewSet pro správu produktů. Obsahuje standardní CRUD operace,
    vlastní endpointy pro vyhledávání, hromadné vytvoření, zásoby a filtrování podle klienta.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = CustomPageNumberPagination

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