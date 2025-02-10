from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from operation.models import Operation
from operation.serializers import OperationSerializer
from operation.services.operation_service import *


class OperationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pro obecnou správu operací (CRUD).
    """
    queryset = Operation.objects.all()
    serializer_class = OperationSerializer


### 🔹 Obecná metoda pro vytvoření operace (IN / OUT) ###

@api_view(['POST'])
def create_operation_view(request, operation_type):
    """
    Endpoint pro vytvoření operace (výdejky nebo příjemky).
    """
    if operation_type not in ['IN', 'OUT']:
        return Response({"error": "Neplatný typ operace. Použijte 'IN' nebo 'OUT'."}, status=400)

    try:
        operation = create_operation(
            user=request.user,
            operation_type=operation_type,
            description=request.data.get('description')
        )
        return Response({
            "message": f"{'Příjemka' if operation_type == 'IN' else 'Výdejka'} byla vytvořena.",
            "operation_id": operation.id
        }, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


### 🔹 Obecná metoda pro přidání skupiny do operace ###

@api_view(['POST'])
def add_group_to_operation_view(request, operation_id):
    """
    Endpoint pro přidání skupiny do operace (výdejky nebo příjemky).
    """
    operation = get_object_or_404(Operation, id=operation_id)

    try:
        if operation.type == 'OUT':
            group = add_group_to_out_operation(
                operation=operation,
                batch_id=request.data['batch_id'],
                box_id=request.data.get('box_id'),
                quantity=request.data['quantity']
            )
        else:  # Příjemka (IN)
            group = add_group_to_in_operation(
                operation=operation,
                product_id=request.data['product_id'],
                batch_number=request.data['batch_number'],
                box_id=request.data.get('box_id'),
                quantity=request.data['quantity'],
                expiration_date=request.data.get('expiration_date')
            )

        return Response({
            "message": "Skupina byla přidána do operace.",
            "group_id": group.id
        }, status=201)

    except ValueError as e:
        return Response({"error": str(e)}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


### 🔹 Rezervace šarží pro výdej ###

@api_view(['POST'])
def reserve_batches_view(request, operation_id):
    """
    Endpoint pro rezervaci šarží ve výdejce.
    """
    operation = get_object_or_404(Operation, id=operation_id, type='OUT')

    try:
        result = reserve_batches_for_out_operation_with_notification(operation)
        return Response(result, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


### 🔹 Zpracování operace (výdej / příjem) ###

@api_view(['POST'])
def process_operation_view(request, operation_id):
    """
    Endpoint pro zpracování operace (výdejky nebo příjemky).
    """
    operation = get_object_or_404(Operation, id=operation_id)

    try:
        if operation.type == 'OUT':
            result = process_out_operation(operation)
        else:  # Příjemka (IN)
            result = process_in_operation(operation)

        return Response(result, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


### 🔹 Přidání skupin na základě strategie (pouze výdej) ###

@api_view(['POST'])
def add_groups_with_strategy_view(request, operation_id):
    """
    Endpoint pro automatické přidání skupin do výdejky na základě strategie.
    """
    operation = get_object_or_404(Operation, id=operation_id, type='OUT')

    try:
        strategy = request.data.get('strategy', 'FIFO')
        product_id = request.data['product_id']
        quantity = request.data['quantity']

        result = add_groups_to_operation_with_strategy(
            operation=operation,
            product_id=product_id,
            quantity=quantity,
            strategy=strategy
        )
        return Response(result, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


### 🔹 Kompletní proces výdeje ###

@api_view(['POST'])
def process_complete_out_operation_view(request):
    """
    Endpoint pro kompletní proces výdeje od vytvoření operace po zpracování.
    """
    try:
        user = request.user
        product_id = request.data['product_id']
        quantity = request.data['quantity']
        strategy = request.data.get('strategy', 'FIFO')
        description = request.data.get('description')

        result = process_complete_out_operation(
            user=user,
            product_id=product_id,
            quantity=quantity,
            strategy=strategy,
            description=description
        )
        return Response(result, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=400)


### 🔹 Storno operace (výdejka / příjemka) ###

@api_view(['POST'])
def cancel_operation_view(request, operation_id):
    """
    Endpoint pro storno operace.
    """
    operation = get_object_or_404(Operation, id=operation_id)

    try:
        result = cancel_operation(operation)
        return Response(result, status=200)

    except ValueError as e:
        return Response({"error": str(e)}, status=400)
    except Exception as e:
        return Response({"error": str(e)}, status=400)
