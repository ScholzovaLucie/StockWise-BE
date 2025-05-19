from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
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
    ViewSet pro práci s historií záznamů v systému.
    Umožňuje základní CRUD operace a také filtrování historie podle typu objektu.
    """
    queryset = History.objects.all()
    serializer_class = HistorySerializer

    @swagger_auto_schema(
        operation_description="Vrací seznam všech záznamů historie.",
        responses={200: HistorySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vytvoří nový záznam historie.",
        responses={201: HistorySerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vrací detail záznamu historie podle ID.",
        responses={200: HistorySerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Upraví celý záznam historie (PUT).",
        responses={200: HistorySerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Částečně upraví záznam historie (PATCH).",
        responses={200: HistorySerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Smaže záznam historie podle ID.",
        responses={204: "No Content"}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter("q", openapi.IN_QUERY, description="Hledaný výraz, lze zadat více oddělené čárkou",
                              type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("page_size", openapi.IN_QUERY, description="Počet záznamů na stránku",
                              type=openapi.TYPE_INTEGER)
        ],
        operation_description="Vyhledává historii podle popisu, typu nebo ID.",
        responses={200: HistorySerializer(many=True)}
    )
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

    @staticmethod
    def _swagger_history_by_type(description):
        return swagger_auto_schema(
            manual_parameters=[
                openapi.Parameter("related_id", openapi.IN_QUERY, description="ID související entity",
                                  type=openapi.TYPE_STRING),
                openapi.Parameter("page_size", openapi.IN_QUERY, description="Počet záznamů na stránku",
                                  type=openapi.TYPE_INTEGER)
            ],
            operation_description=description,
            responses={200: HistorySerializer(many=True)}
        )

    @_swagger_history_by_type("Vrací historii typu 'operation'.")
    @action(detail=False, methods=["get"], url_path="operation")
    def get_operation_history(self, request):
        """
        Vrací historii typu 'operation'.
        """
        return self._get_paginated_response_by_type(request, "operation")

    @_swagger_history_by_type("Vrací historii typu 'product'.")
    @action(detail=False, methods=["get"], url_path="product")
    def get_product_history(self, request):
        """
        Vrací historii typu 'product'.
        """
        return self._get_paginated_response_by_type(request, "product")

    @_swagger_history_by_type("Vrací historii typu 'position'.")
    @action(detail=False, methods=["get"], url_path="position")
    def get_position_history(self, request):
        """
        Vrací historii typu 'position'.
        """
        return self._get_paginated_response_by_type(request, "position")

    @_swagger_history_by_type("Vrací historii typu 'batch'.")
    @action(detail=False, methods=["get"], url_path="batch")
    def get_batch_history(self, request):
        """
        Vrací historii typu 'batch'.
        """
        return self._get_paginated_response_by_type(request, "batch")

    @_swagger_history_by_type("Vrací historii typu 'group'.")
    @action(detail=False, methods=["get"], url_path="group")
    def get_group_history(self, request):
        """
        Vrací historii typu 'group'.
        """
        return self._get_paginated_response_by_type(request, "group")