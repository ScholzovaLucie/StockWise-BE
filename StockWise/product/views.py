from rest_framework import viewsets, status, generics, mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.response import Response

from product.models import Product
from product.serializers import ProductSerializer


class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# Create your views here.
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = ProductPagination

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        is_many = isinstance(request.data, list)

        # Validace a uložení dat
        serializer = ProductSerializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)

        if is_many:
            products = Product.objects.bulk_create([Product(**item) for item in serializer.validated_data])
            return Response(ProductSerializer(products, many=True).data, status=status.HTTP_201_CREATED)

        product = serializer.save()
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)

