from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework import viewsets, status

from history.models import History
from history.serializers import HistorySerializer
from django.db.models import Q
from functools import reduce
from operator import or_

from utils.pagination import CustomPageNumberPagination


class HistoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet pro práci s historií. Umožňuje vyhledávání a filtrování záznamů podle typu.
    """
    queryset = History.objects.all()
    serializer_class = HistorySerializer

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """
        Vyhledává historii podle dotazu v popisu, typu nebo ID.

        :param request: HTTP GET s parametrem "q" (řetězec nebo čárkami oddělené hodnoty)
        :return: Paginovaná odpověď se záznamy historie odpovídajícími hledání
        """
        query = request.GET.get("q", "").strip()

        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        query_terms = [term.strip() for term in query.split(",") if term.strip()]

        search_query = reduce(or_, [
            Q(description__icontains=term) |
            Q(related_id__icontains=term) |
            Q(type__icontains=term)
            for term in query_terms
        ])

        history = History.objects.filter(search_query).select_related("user")

        paginator = CustomPageNumberPagination()
        paginator.page_size = request.GET.get("page_size", 10)
        paginated_data = paginator.paginate_queryset(history, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return paginator.get_paginated_response(serializer.data)

    def _get_paginated_response_by_type(self, request, type_value):
        """
        Vrací paginovanou historii podle zadaného typu (operation, product, batch atd.) a volitelného related_id.

        :param request: HTTP GET požadavek s volitelným parametrem 'related_id' a 'page_size'
        :param type_value: Typ historie (např. 'operation', 'product')
        :return: Paginovaná odpověď se záznamy historie daného typu
        """
        related_id = request.GET.get("related_id", None)
        queryset = History.objects.filter(type=type_value)

        if related_id is not None:
            queryset = queryset.filter(related_id=related_id)

        paginator = CustomPageNumberPagination()
        paginator.page_size = request.GET.get("page_size", 10)
        paginated_data = paginator.paginate_queryset(queryset, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="operation")
    def get_operation_history(self, request):
        """
        Vrací historii typu 'operation'.
        """
        return self._get_paginated_response_by_type(request, "operation")

    @action(detail=False, methods=["get"], url_path="product")
    def get_product_history(self, request):
        """
        Vrací historii typu 'product'.
        """
        return self._get_paginated_response_by_type(request, "product")

    @action(detail=False, methods=["get"], url_path="position")
    def get_position_history(self, request):
        """
        Vrací historii typu 'position'.
        """
        return self._get_paginated_response_by_type(request, "position")

    @action(detail=False, methods=["get"], url_path="batch")
    def get_batch_history(self, request):
        """
        Vrací historii typu 'batch'.
        """
        return self._get_paginated_response_by_type(request, "batch")

    @action(detail=False, methods=["get"], url_path="group")
    def get_group_history(self, request):
        """
        Vrací historii typu 'group'.
        """
        return self._get_paginated_response_by_type(request, "group")