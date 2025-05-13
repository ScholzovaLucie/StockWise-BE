from functools import reduce

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Prefetch

from box.models import Box
from box.serializers import BoxSerializer
from group.models import Group
from utils.pagination import CustomPageNumberPagination


class BoxViewSet(viewsets.ModelViewSet):
    queryset = Box.objects.all()
    serializer_class = BoxSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        """
        Načítá boxy s přednačtením ID skupin (pro optimalizaci)
        """
        return Box.objects.prefetch_related(
            Prefetch('groups', queryset=Group.objects.only('id'))
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