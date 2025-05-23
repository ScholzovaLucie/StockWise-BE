from functools import reduce

from django.db.models import Prefetch
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from operation.serializers import OperationSerializer, OperationListSerializer
from operation.services.operation_service import *
from django.db.models import Q

from utils.pagination import CustomPageNumberPagination


class OperationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    OperationViewSet poskytuje rozhraní pro čtení operací v systému skladového hospodářství.

    Funkcionalita zahrnuje:
    - seznam operací a detail konkrétní operace (ReadOnlyModelViewSet)
    - akci `/search/` pro fulltextové vyhledávání operací (číslo, šarže, produkt, status, typ)
    - akce `/types/` a `/statuses/` pro získání seznamu všech typů a stavů operací
    - akci `/all/` pro načtení všech operací s možností stránkování
    - akci `/create/` pro vytvoření nové operace typu `IN` nebo `OUT`
    - akce pro detail, aktualizaci, smazání a změnu statusu operace
    - pokročilé akce: přidání produktu do krabice, uzavření krabice, zahájení a dokončení balení
    - optimalizované dotazy pomocí `prefetch_related` pro výkon
    - filtrace operací podle klienta přihlášeného uživatele (`request.user.client`)
    - použití vlastního stránkovače `CustomPageNumberPagination`

    Všechny endpointy vyžadují autentizaci a jsou chráněny pomocí `IsAuthenticated`.
    """
    queryset = Operation.objects.all()
    serializer_class = OperationSerializer
    pagination_class = CustomPageNumberPagination
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Vrací seznam operací pro přihlášeného uživatele (klienta).",
        responses={200: OperationListSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Vrací detail konkrétní operace podle ID.",
        responses={200: OperationSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def get_serializer_class(self):
        """
        Vrací serializer podle akce (zkrácený pro list).

        :return: Třída serializeru
        """
        if self.action == 'list':
            return OperationListSerializer
        return OperationSerializer

    def get_queryset(self):
        """
        Vrací queryset operací dle oprávnění uživatele a klienta.

        :return: Queryset operací
        """
        client_id = self.request.GET.get('client')
        client_ids = list(self.request.user.client.values_list('id', flat=True))

        groups_qs = Group.objects.select_related(
            'batch__product',
            'box'
        ).select_related(
            'batch'
        )
        prefetch = Prefetch('groups', queryset=groups_qs, to_attr='prefetched_groups')

        queryset = Operation.objects.prefetch_related(prefetch).select_related('client').order_by('-updated_at')

        if client_id and int(client_id) in client_ids:
            queryset = queryset.filter(client_id=client_id)
        else:
            queryset = queryset.filter(client_id__in=client_ids)

        return queryset

    @swagger_auto_schema(
        operation_description="Vyhledávání operací podle více polí (číslo, šarže, SKU, název, typ, status).",
        manual_parameters=[
            openapi.Parameter("q", openapi.IN_QUERY, description="Vyhledávací dotaz", type=openapi.TYPE_STRING),
            openapi.Parameter("clientId", openapi.IN_QUERY, description="ID klienta", type=openapi.TYPE_STRING),
        ],
        responses={200: OperationListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Vyhledávání operací podle více polí (číslo, šarže, SKU, název, typ, status).

        :param request: HTTP požadavek s parametrem 'q'
        :return: Paginated response s výsledky vyhledávání
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
                                Q(number=term) |
                                Q(groups__batch__batch_number=term) |
                                Q(groups__batch__product__sku=term) |
                                Q(groups__batch__product__name=term) |
                                Q(type=term) |
                                Q(status=term),
                data_query,
                Q()
            )
            operations = Operation.objects.filter(query_filters).only("id")
        else:
            operations = Operation.objects.filter(
                Q(number=query) |
                Q(groups__batch__batch_number=query) |
                Q(groups__batch__product__sku=query) |
                Q(groups__batch__product__name=query) |
                Q(type=query) |
                Q(status=query),
            ).only("id")

        if client_id:
            operations = operations.filter(client_id=client_id)

        paginator = CustomPageNumberPagination()
        paginator.page_size = request.GET.get('page_size') or 10
        paginated_data = paginator.paginate_queryset(operations, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        operation_description="Vrací seznam typů operací.",
        responses={200: openapi.Response("Seznam typů", schema=openapi.Schema(type=openapi.TYPE_OBJECT))}
    )
    @action(detail=False, methods=['get'], url_path='types')
    def get_types(self, request):
        """
        Vrací seznam typů operací.
        """
        return Response({"data": [choice[0] for choice in Operation.OPERATION_TYPE_CHOICES]}, status=200)

    @swagger_auto_schema(
        operation_description="Vrací seznam statusů operací.",
        responses={200: openapi.Response("Seznam statusů", schema=openapi.Schema(type=openapi.TYPE_OBJECT))}
    )
    @action(detail=False, methods=['get'], url_path='statuses')
    def get_statuses(self, request):
        """
        Vrací seznam statusů operací.
        """
        return Response({"data": [choice[0] for choice in Operation.OPERATION_STATUS_CHOICES]}, status=200)

    @swagger_auto_schema(
        operation_description="Vrací seznam všech operací s možností stránkování.",
        responses={200: OperationListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='all')
    def get_all_operations(self, request):
        """
        Vrací seznam všech operací s možností stránkování.
        """
        operations = self.get_queryset()
        paginator = CustomPageNumberPagination()
        paginator.page_size = request.GET.get('page_size') or 10
        paginated_data = paginator.paginate_queryset(operations, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return paginator.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        operation_description="Vytváří novou operaci typu 'IN' nebo 'OUT'.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'type': openapi.Schema(type=openapi.TYPE_STRING),
                'number': openapi.Schema(type=openapi.TYPE_STRING),
                'description': openapi.Schema(type=openapi.TYPE_STRING),
                'client_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'products': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
            },
            required=['type', 'number', 'client_id', 'products']
        ),
        responses={201: openapi.Response(description="Operace vytvořena")}
    )
    @action(detail=False, methods=['post'], url_path='create')
    def create_operation(self, request):
        """
        Vytváří novou operaci typu 'IN' nebo 'OUT'.

        :param request: HTTP POST s daty operace
        :return: JSON odpověď s ID vytvořené operace
        """
        operation_type = request.data.get('type')
        number = request.data.get('number')
        description = request.data.get('description')
        client_id = request.data.get('client_id')
        products = request.data.get('products')

        if not number or not operation_type or not client_id or not products:
            return Response({"error": "Chybějící povinný parametr."}, status=400)

        if operation_type not in ['IN', 'OUT']:
            return Response({"error": "Neplatný typ operace. Použijte 'IN' nebo 'OUT'."}, status=400)

        try:
            operation = create_operation(
                user=request.user,
                operation_type=operation_type,
                description=description,
                number=number,
                client_id=client_id,
                products=products,
                delivery_data={...},
                invoice_data={...}
            )
            return Response({
                "message": f"{'Příjemka' if operation_type == 'IN' else 'Výdejka'} byla vytvořena.",
                "operation_id": operation.id
            }, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @swagger_auto_schema(
        operation_description="Vrací detail konkrétní operace.",
        responses={200: OperationSerializer()}
    )
    @action(detail=True, methods=['get'], url_path='')
    def get_operation_detail(self, request, pk=None):
        """
        Vrací detail konkrétní operace.

        :param pk: ID operace
        :return: JSON s daty operace
        """
        operation = get_object_or_404(Operation, id=pk)
        serializer = OperationSerializer(operation)
        return Response(serializer.data, status=200)

    @swagger_auto_schema(
        operation_description="Aktualizace operace podle zadaného ID.",
        request_body=OperationSerializer(),
        responses={200: openapi.Response(description="Aktualizováno")}
    )
    @action(detail=True, methods=['patch'], url_path='update')
    def update_operation(self, request, pk=None):
        """
        Aktualizace operace podle zadaného ID.

        :param pk: ID operace
        :param request: HTTP PATCH požadavek s aktualizačními daty
        :return: JSON s potvrzením nebo chybou
        """
        operation = get_object_or_404(Operation, id=pk)
        try:
            updated_operation = update_operation(operation, request.data)
            return Response({"message": "Operace byla úspěšně aktualizována.", "operation_id": updated_operation.id}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @swagger_auto_schema(
        operation_description="Vymaže operaci podle ID.",
        responses={200: openapi.Response(description="Smazáno")}
    )
    @action(detail=True, methods=['delete'], url_path='remove')
    def remove_operation(self, request, pk=None):
        """
        Vymaže operaci podle ID.

        :param pk: ID operace
        :return: JSON odpověď s potvrzením nebo chybou
        """
        operation = get_object_or_404(Operation, id=pk)
        try:
            remove_operation(operation)
            return Response({"message": "Operace byla úspěšně smazána."}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @swagger_auto_schema(
        operation_description="Aktualizuje status dané operace.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'status': openapi.Schema(type=openapi.TYPE_STRING)},
            required=['status']
        ),
        responses={200: openapi.Response(description="Status změněn")}
    )
    @action(detail=True, methods=['patch'], url_path='update_status')
    def update_status(self, request, pk=None):
        """
        Aktualizuje status dané operace.

        :param pk: ID operace
        :return: JSON odpověď s potvrzením nebo chybou
        """
        operation = get_object_or_404(Operation, id=pk)
        new_status = request.data.get('status')
        try:
            operation.status = new_status
            operation.save(user=request.user)
            return Response({"message": "Status úěspěšně změněn"}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @swagger_auto_schema(
        operation_description="Přidá produkt z operace do zvolené krabice.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'box_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'product_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER)
            },
            required=['box_id', 'product_id', 'quantity']
        ),
        responses={200: openapi.Response(description="Produkt přidán")}
    )
    @action(detail=True, methods=['post'], url_path='add_to_box')
    def add_to_box(self, request, pk=None):
        """
        Přidá produkt z operace do zvolené krabice.

        :param pk: ID operace
        :return: JSON s výsledkem
        """
        box_id = request.data.get('box_id')
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity'))

        result = add_product_to_box(pk, box_id, product_id, quantity)
        return Response(result, status=200)

    @swagger_auto_schema(
        operation_description="Vrací přehled produktů a jejich množství v dané operaci.",
        responses={200: openapi.Response(description="Přehled produktů")}
    )
    @action(detail=True, methods=['get'], url_path='product_summary')
    def product_summary(self, request, pk=None):
        """
        Vrací přehled produktů a jejich množství v dané operaci.

        :param pk: ID operace
        :return: JSON s přehledem produktů
        """
        summary = get_operation_product_summary(pk)
        return Response(summary, status=200)

    @swagger_auto_schema(
        operation_description="Uzavře krabici podle ID.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={'box_id': openapi.Schema(type=openapi.TYPE_INTEGER)},
            required=['box_id']
        ),
        responses={200: openapi.Response(description="Krabice uzavřena")}
    )
    @action(detail=True, methods=['post'], url_path='close_box')
    def close_box(self, request, pk=None):
        """
        Uzavře krabici podle ID.

        :param request: HTTP POST s 'box_id'
        :return: JSON s potvrzením
        """
        box_id = request.data.get('box_id')
        box = Box.objects.get(id=box_id)
        box.closed = True
        box.save()
        return Response({"message": "Krabice uzavřena"}, status=200)

    @swagger_auto_schema(
        operation_description="Změní status operace na 'BOX', značí začátek balení.",
        responses={200: openapi.Response(description="Status změněn")}
    )
    @action(detail=True, methods=['post'], url_path='start_packaging')
    def start_packaging(self, request, pk=None):
        """
        Změní status operace na 'BOX', značí začátek balení.

        :param pk: ID operace
        :return: JSON s potvrzením
        """
        try:
            operation = get_object_or_404(Operation, id=pk)
            operation.status = 'BOX'
            operation.save()
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        return Response({"message": "Krabice uzavřena"}, status=200)

    @swagger_auto_schema(
        operation_description="Dokončí balení operace, nastaví status na 'COMPLETED'.",
        responses={200: openapi.Response(description="Dokončeno")}
    )
    @action(detail=True, methods=['post'], url_path='complete_packing')
    def complete_packing(self, request, pk=None):
        """
        Dokončí balení operace, nastaví status na 'COMPLETED'.

        :param pk: ID operace
        :return: JSON s potvrzením nebo chybou
        """
        operation = get_object_or_404(Operation, id=pk)

        if operation.status != "BOX":
            return Response({"error": "Operace není ve stavu BOX"}, status=400)

        operation.status = "COMPLETED"
        operation.save()

        return Response({"message": "Operace byla úspěšně dokončena"}, status=200)