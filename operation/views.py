from functools import reduce

from django.db.models import Prefetch
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from operation.models import Operation
from operation.serializers import OperationSerializer, OperationListSerializer
from operation.services.operation_service import *

class OperationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pro správu operací (CRUD).
    """
    queryset = Operation.objects.all()
    serializer_class = OperationSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return OperationListSerializer
        return OperationSerializer

    def get_queryset(self):
        client_id = self.request.GET.get('client')
        client_ids = list(self.request.user.client.values_list('id', flat=True))

        groups_qs = Group.objects.select_related(
            'batch__product', 'box'
        )

        queryset = Operation.objects.prefetch_related(
            Prefetch('groups', queryset=groups_qs)
        ).select_related('client').order_by('-updated_at')

        if client_id and int(client_id) in client_ids:
            queryset = queryset.filter(client_id=client_id)
        else:
            queryset = queryset.filter(client_id__in=client_ids)

        return queryset

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
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
                                Q(groups__batch__batch_number=term)|
                                Q(groups__batch__product__sku=term)|
                                Q(groups__batch__product__name=term)|
                                Q(type=term)|
                                Q(status=term) ,
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

        paginator = PageNumberPagination()
        paginator.page_size = request.GET.get('page_size') or 10
        paginated_data = paginator.paginate_queryset(operations, request)

        serializer = self.get_serializer(paginated_data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='types')
    def get_types(self, request):
        """Vrací seznam typů operací."""
        return Response({"data": [choice[0] for choice in Operation.OPERATION_TYPE_CHOICES]}, status=200)

    @action(detail=False, methods=['get'], url_path='statuses')
    def get_statuses(self, request):
        """Vrací seznam statusů operací."""
        return Response({"data": [choice[0] for choice in Operation.OPERATION_STATUS_CHOICES]}, status=200)

    @action(detail=False, methods=['get'], url_path='all')
    def get_all_operations(self, request):
        """Vrátí seznam všech operací (objednávek)."""
        operations = Operation.objects.all()
        serializer = OperationSerializer(operations, many=True)
        return Response(serializer.data, status=200)

    @action(detail=False, methods=['post'], url_path='create')
    def create_operation(self, request):
        """Vytvoření operace."""
        operation_type = request.data.get('type')
        number = request.data.get('number')
        description = request.data.get('description')
        client_id = request.data.get('client_id')
        products = request.data.get('products')

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
                delivery_data={
                    'delivery_name': request.get("delivery_name", ""),
                    'delivery_street': request.get("delivery_street", ""),
                    'delivery_city': request.get("delivery_city", ""),
                    'delivery_psc': request.get("delivery_psc", ""),
                    'delivery_country':request.get("delivery_country", ""),
                    'delivery_phone': request.get("delivery_phone", ""),
                    'delivery_email': request.get("delivery_email", ""),
                },
                invoice_data={
                    'invoice_name': request.get("invoice_name", ""),
                    'invoice_street': request.get("invoice_street", ""),
                    'invoice_city': request.get("invoice_city", ""),
                    'invoice_psc': request.get("invoice_psc", ""),
                    'invoice_country': request.get("invoice_country", ""),
                    'invoice_phone': request.get("invoice_phone", ""),
                    'invoice_email': request.get("invoice_email", ""),
                    'invoice_ico': request.get("invoice_ico", ""),
                    'invoice_vat': request.get("invoice_vat", ""),
                }
            )
            return Response({
                "message": f"{'Příjemka' if operation_type == 'IN' else 'Výdejka'} byla vytvořena.",
                "operation_id": operation.id
            }, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['get'], url_path='')
    def get_operation_detail(self, request, pk=None):
        """Vrací detail konkrétní operace."""
        operation = get_object_or_404(Operation, id=pk)
        serializer = OperationSerializer(operation)
        return Response(serializer.data, status=200)

    @action(detail=True, methods=['post'], url_path='process')
    def process_operation(self, request, pk=None):
        """Zpracování operace (výdejka/příjemka)."""
        operation = get_object_or_404(Operation, id=pk)

        try:
            if operation.type == 'OUT':
                result = process_out_operation(operation)
            else:  # Příjemka (IN)
                result = process_in_operation(operation)

            return Response(result, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['patch'], url_path='update')
    def update_operation(self, request, pk=None):
        """Aktualizace operace."""
        operation = get_object_or_404(Operation, id=pk)

        try:
            updated_operation = update_operation(operation, request.data)
            return Response({"message": "Operace byla úspěšně aktualizována.", "operation_id": updated_operation.id}, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['delete'], url_path='remove')
    def remove_operation(self, request, pk=None):
        """Vymaže danou objednávku"""
        operation = get_object_or_404(Operation, id=pk)
        try:
            remove_operation(operation)
            return Response({"message": "Operace byla úspěšně smazána."},
                            status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['patch'], url_path='update_status')
    def update_status(self, request, pk=None):
        """API pro změnu statusu operace"""
        operation = get_object_or_404(Operation, id=pk)
        new_status = request.data.get('status')

        try:
            operation.status = new_status
            operation.save(user=request.user)
            return Response({"message": "Status úspěšně změněn"}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

    @action(detail=True, methods=['post'], url_path='add_to_box')
    def add_to_box(self, request, pk=None):
        """Přidání produktu do krabice"""
        box_id = request.data.get('box_id')
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity'))

        result = add_product_to_box(pk, box_id, product_id, quantity)

        return Response(result, status=200)

    @action(detail=True, methods=['get'], url_path='product_summary')
    def product_summary(self, request, pk=None):
        """Vrací seznam produktů a jejich celkové množství v operaci"""
        summary = get_operation_product_summary(pk)
        return Response(summary, status=200)

    @action(detail=True, methods=['post'], url_path='close_box')
    def close_box(self, request, pk=None):
        """Uzavření krabice"""
        box_id = request.data.get('box_id')
        box = Box.objects.get(id=box_id)
        box.closed = True
        box.save()

        return Response({"message": "Krabice uzavřena"}, status=200)

    @action(detail=True, methods=['post'], url_path='start_packaging')
    def start_packaging(self, request, pk=None):
        """Uzavření krabice"""
        try:
            operation = get_object_or_404(Operation, id=pk)
            operation.status = 'BOX'
            operation.save()
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        return Response({"message": "Krabice uzavřena"}, status=200)

    @action(detail=True, methods=['post'], url_path='complete_packing')
    def complete_packing(self, request, pk=None):
        """Dokončení balení a operace"""
        operation = get_object_or_404(Operation, id=pk)

        if operation.status != "BOX":
            return Response({"error": "Operace není ve stavu BOX"}, status=400)

        operation.status = "COMPLETED"
        operation.save()

        return Response({"message": "Operace byla úspěšně dokončena"}, status=200)