from functools import reduce
from itertools import chain

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Sum

from group.models import Group
from product.models import Product
from product.serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        """
        Umožňuje filtrovat produkty podle klienta.
        """
        queryset = Product.objects.all()
        client_id = self.request.GET.get('client')
        client_ids = self.request.user.client.all().values_list('id', flat=True)
        queryset = queryset.filter(client_id__in=client_ids)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        return queryset

    @action(detail=False, methods=['get'], url_path='by-client/(?P<client_id>[^/.]+)')
    def get_products_by_client(self, request, client_id=None):
        """
        Vrací seznam produktů patřících konkrétnímu klientovi.
        """
        products = Product.objects.filter(client_id=client_id)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Hromadné vytvoření více produktů najednou.
        """
        is_many = isinstance(request.data, list)
        serializer = ProductSerializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)

        if is_many:
            products = Product.objects.bulk_create([Product(**item) for item in serializer.validated_data])
            return Response(ProductSerializer(products, many=True).data, status=status.HTTP_201_CREATED)

        product = serializer.save()
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Vyhledání produktů podle názvu, popisu nebo SKU.
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
                                Q(name__icontains=term) |
                                Q(description__icontains=term) |
                                Q(sku__icontains=term),
                data_query,
                Q()
            )

            products = Product.objects.filter(query_filters).distinct()

        else:
            products = Product.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query) | Q(sku__icontains=query)
            )

        if client_id:
            products = products.filter(client_id=client_id)

        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='stock')
    def get_product_stock(self, request, pk=None):
        """
        Vrátí dostupné množství produktu ve všech dostupných šaržích.
        """
        try:
            product = Product.objects.get(id=pk)
            return Response({"available": product.amount}, status=200)
        except Product.DoesNotExist:
            return Response({"error": "Produkt nebyl nalezen"}, status=404)