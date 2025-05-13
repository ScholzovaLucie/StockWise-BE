from datetime import datetime, timedelta

from django.conf import settings
from django.http import JsonResponse

from batch.models import Batch
from batch.serializers import BatchSerializer, BatchBulkSerializer
from box.models import Box
from client.models import Client
from client.serializers import ClientSerializer, ClientBulkSerializer
from group.models import Group
from group.serializers import GroupSerializer, GroupBulkSerializer
from history.models import History
from history.serializers import HistorySerializer
from operation.models import Operation
from operation.serializers import OperationSerializer, OutOperationSerializer, InOperationSerializer
from position.models import Position
from position.serializers import PositionSerializer, PositionBulkSerializer
from product.models import Product
from product.serializers import ProductSerializer, ProductBulkSerializer
from user.models import User
from user.serializers import UserSerializer, UserBulkSerializer
from warehouse.models import Warehouse
from warehouse.serializers import WarehouseSerializer, WarehouseBulkSerializer

def with_type(func, history_type):
    """
    Pomocná funkce pro vložení typu historie do volané funkce.

    :param func: Funkce pro zpracování historie
    :param history_type: Typ historie (např. 'batch', 'operation')
    :return: Lambda funkce volající `func` s dodaným typem
    """
    return lambda call_id, parameters, client_id, model, serializer, user: \
        func(call_id, parameters, client_id, model, serializer, user, history_type)


def get_function(function_name):
    available_functions = {
        """
        Vrací trojici (funkce, model, serializer) podle názvu funkce.

        :param function_name: Název funkce (např. 'getProducts')
        :return: Tuple (funkce, model, serializer)
        """
        # GET funkce – získání dat
        'getBatches': (AssistantDataCreator().get_data, Batch, BatchSerializer),
        'getClients': (AssistantDataCreator().get_data, Client, ClientSerializer),
        'getGroups': (AssistantDataCreator().get_data, Group, GroupSerializer),
        'getOperations': (AssistantDataCreator().get_data, Operation, OperationSerializer),
        'getPositions': (AssistantDataCreator().get_data, Position, PositionSerializer),
        'getProducts': (AssistantDataCreator().get_data, Product, ProductSerializer),
        'getUsers': (AssistantDataCreator().get_data, User, UserSerializer),
        'getWarehouses': (AssistantDataCreator().get_data, Warehouse, WarehouseSerializer),
        'getOperationStatuses': (AssistantDataCreator().get_operation_statuses, Operation, OperationSerializer),
        'getHistory': (AssistantDataCreator().get_history_data, History, HistorySerializer),
        'getOperationHistory': (with_type(AssistantDataCreator().get_specific_history_data, 'operation'), History, HistorySerializer),
        'getProductHistory': (with_type(AssistantDataCreator().get_specific_history_data, 'product'), History, HistorySerializer),
        'getBatchHistory': (with_type(AssistantDataCreator().get_specific_history_data, 'batch'), History, HistorySerializer),
        'getGroupHistory': (with_type(AssistantDataCreator().get_specific_history_data, 'group'), History, HistorySerializer),
        'getPositionHistory': (with_type(AssistantDataCreator().get_specific_history_data, 'position'), History, HistorySerializer),

        # POST funkce – vytvoření objektů (single/bulk)
        'createBatch': (AssistantDataCreator().create_data, Batch, BatchSerializer),
        'createClient': (AssistantDataCreator().create_data, Client, ClientSerializer),
        'createGroup': (AssistantDataCreator().create_data, Group, GroupSerializer),
        'createOutOperation': (AssistantDataCreator().create_data, Operation, OutOperationSerializer),
        'createInOperation': (AssistantDataCreator().create_data, Operation, InOperationSerializer),
        'createPosition': (AssistantDataCreator().create_data, Position, PositionSerializer),
        'createProduct': (AssistantDataCreator().create_data, Product, ProductSerializer),
        'createUser': (AssistantDataCreator().create_data, User, UserSerializer),
        'createWarehouse': (AssistantDataCreator().create_data, Warehouse, WarehouseSerializer),

        'createBatches': (AssistantDataCreator().bulk_create_data, Batch, BatchBulkSerializer),
        'createProducts': (AssistantDataCreator().bulk_create_data, Product, ProductBulkSerializer),
        'createGroups': (AssistantDataCreator().bulk_create_data, Group, GroupBulkSerializer),
        'createClients': (AssistantDataCreator().bulk_create_data, Client, ClientBulkSerializer),
        'createWarehouses': (AssistantDataCreator().bulk_create_data, Warehouse, WarehouseBulkSerializer),
        'createOutOperations': (AssistantDataCreator().bulk_create_data, Operation, OutOperationSerializer),
        'createInOperations': (AssistantDataCreator().bulk_create_data, Operation, InOperationSerializer),
        'createPositions': (AssistantDataCreator().bulk_create_data, Position, PositionBulkSerializer),
        'createUsers': (AssistantDataCreator().bulk_create_data, User, UserBulkSerializer),

        # UPDATE funkce – aktualizace dat
        'updateBatch': (AssistantDataCreator().update_data, Batch, BatchSerializer),
        'updateClient': (AssistantDataCreator().update_data, Client, ClientSerializer),
        'updateGroup': (AssistantDataCreator().update_data, Group, GroupSerializer),
        'updateOperation': (AssistantDataCreator().update_data, Operation, OperationSerializer),
        'updatePosition': (AssistantDataCreator().update_data, Position, PositionSerializer),
        'updateProduct': (AssistantDataCreator().update_data, Product, ProductSerializer),
        'updateUser': (AssistantDataCreator().update_data, User, UserSerializer),
        'updateWarehouse': (AssistantDataCreator().update_data, Warehouse, WarehouseSerializer),
    }
    return available_functions[function_name]


class AssistantDataCreator(object):
    def get_history_data(self, call_id, parameters, client_id, model, serializer, user):
        """
        Získá historii dle zadaných parametrů.

        :param call_id: ID volání nástroje
        :param parameters: Parametry pro filtrování
        :param client_id: ID klienta
        :param model: Model (např. History)
        :param serializer: Serializér pro model
        :param user: Uživatel volající funkci
        :return: Formátovaná historie jako dict
        """
        data_query = model.objects.all()

        if 'type' in parameters:
            data_query = data_query.filter(type=parameters['type'])

        if 'from_timestamp' in parameters:
            data_query = data_query.filter(timestamp__gte=parameters['from_timestamp'])
        if 'to_timestamp' in parameters:
            data_query = data_query.filter(timestamp__lte=parameters['to_timestamp'])

        return self.format_data(HistorySerializer, data_query, call_id)

    def get_specific_history_data(self, call_id, parameters, client_id, model, serializer, user, history_type):
        """
        Získá historii pro specifický typ záznamu.

        :param history_type: Typ historie (např. 'operation')
        :return: Formátovaná historie jako dict
        """
        parameters['type'] = history_type
        return self.get_history_data(call_id, parameters, client_id, model, serializer, user)

    def get_data(self, call_id, parameters, client_id, model, serializer, user):
        """
        Obecné získání dat z daného modelu s volitelným filtrováním.

        :param call_id: ID volání nástroje
        :param parameters: Filtrovací parametry
        :param client_id: ID klienta
        :param model: Django model
        :param serializer: Příslušný serializer
        :param user: Uživatel
        :return: dict
        """
        data_query = model.objects.all()

        if client_id:
            if isinstance(model, Batch):
                data_query = data_query.filter(item__client_id=client_id)
            elif isinstance(model, Client):
                data_query = data_query.filter(id=client_id)
            elif isinstance(model, Group):
                data_query = data_query.filter(batch__item__client_id=model.id)
            elif isinstance(model, Operation):
                data_query = data_query.filter(items__batch__item__client_id=model.id)

        filter_params = ['code', 'ean',]
        for param in filter_params:
            if parameters.get(param) is not None:
                if param == 'created_by_month':
                    data_query = self.filter_by_month(parameters.get(param), data_query, model)
                elif param == 'created_by_year':
                    data_query = self.filter_by_year(parameters.get(param), data_query, model)
                elif param == 'created_by_day':
                    data_query = self.filter_by_day(parameters.get(param), data_query, model)
                else:
                    data_query = data_query.filter(**{param: parameters.get(param)})

        # Vrací pouze počet
        if parameters.get('onlyCount'):
            count_of_data_query = data_query.count()
            return {
                        'tool_call_id': call_id,
                        'output': str(count_of_data_query)
                    }

        return self.format_data(serializer, data_query, call_id)

    def update_data(self, call_id, parameters, client_id, model, serializer, user):
        """
        Aktualizuje instanci modelu podle ID a vstupních parametrů.

        :param call_id: ID volání nástroje
        :param parameters: Aktualizační data (musí obsahovat ID)
        :param client_id: ID klienta (nevyužito)
        :param model: Django model
        :param serializer: Příslušný serializer
        :param user: Uživatel
        :return: dict
        """
        instance_id = parameters.get('id')
        if not instance_id:
            return {
                'tool_call_id': call_id,
                'output': 'ID is required for update'
            }

        try:
            instance = model.objects.get(id=instance_id)
        except model.DoesNotExist:
            return {
                'tool_call_id': call_id,
                'output': f'{model.__name__} with ID {instance_id} not found'
            }

        try:
            serializer_instance = serializer(instance, data=parameters, partial=True)
            if serializer_instance.is_valid():
                serializer_instance.save()
                return {'tool_call_id': call_id, 'output': f'{model.__name__} updated'}
            else:
                return {
                    'tool_call_id': call_id,
                    'output': str(serializer_instance.errors)
                }
        except Exception as e:
            return {
                'tool_call_id': call_id,
                'output': str(e)
            }

    def create_data(self, call_id, parameters, client_id, model, serializer, user):
        """
            Vytvoří novou instanci modelu.

            :param call_id: ID volání nástroje
            :param parameters: Data pro vytvoření
            :param client_id: ID klienta
            :param model: Django model
            :param serializer: Příslušný serializer
            :param user: Uživatel
            :return: dict
            """
        try:
            parameters['user_id'] = user.id
            if client_id:
                parameters['client_id'] = client_id
            serializer_instance = serializer(data=parameters)
            if serializer_instance.is_valid():
                instance = serializer_instance.save()
                return {
                    'tool_call_id': call_id,
                    'output': f'{model} created'
                }
            else:
                return {
                    'tool_call_id': call_id,
                    'output': str(serializer_instance.errors)
                }
        except Exception as e:
            return {
                'tool_call_id': call_id,
                'output': str(e)
            }

    def bulk_create_data(self, call_id, parameters, client_id, model, serializer, user):
        """
        Hromadné vytvoření instancí modelu.

        :param call_id: ID volání nástroje
        :param parameters: Slovník s klíčem "items" – seznam dat
        :param client_id: ID klienta
        :param model: Django model
        :param serializer: Příslušný serializer
        :param user: Uživatel
        :return: dict
        """
        try:
            items = parameters.get('items')
            if not items or not isinstance(items, list):
                return {
                    'tool_call_id': call_id,
                    'output': 'Parameter "items" must be a list of objects'
                }

            for item in items:
                item['user_id'] = user.id
                if client_id:
                    item['client_id'] = client_id

            serializer_instance = serializer(data=items, many=True)
            if serializer_instance.is_valid():
                instances = [model(**item) for item in serializer_instance.validated_data]
                model.objects.bulk_create(instances, batch_size=1000)  # můžeš upravit batch_size dle potřeby
                return {
                    'tool_call_id': call_id,
                    'output': f'{len(instances)} {model.__name__} objects created'
                }
            else:
                return {
                    'tool_call_id': call_id,
                    'output': str(serializer_instance.errors)
                }

        except Exception as e:
            return {
                'tool_call_id': call_id,
                'output': str(e)
            }

    def get_operation_statuses(self, call_id, parameters, client_id, model, serializer, user):
        """
        Vrací seznam dostupných stavů operací.

        :param call_id: ID volání nástroje
        :return: dict
        """
        return {
            'tool_call_id': call_id,
            'output': Operation.OPERATION_STATUS_CHOICES
        }

    @staticmethod
    def format_data(serializer, data_query, call_id):
        """
        Serializuje queryset do JSON formátu.

        :param serializer: Serializér pro výstup
        :param data_query: Queryset s daty
        :param call_id: ID volání nástroje
        :return: dict
        """
        if data_query is []:
            return None

        data = serializer(data_query, many=True).data
        data_bytes = JsonResponse(data, safe=False).content

        outputs = {
            data_bytes.decode("utf-8")
        }
        return {
            'tool_call_id': call_id,
            'output': str(outputs)
        }


    @staticmethod
    def filter_by_year(date, data_query, model):
        """
        Filtrování dat podle roku.

        :param date: Rok
        :param data_query: Queryset
        :param model: Django model
        :return: queryset
        """
        data = None
        if 'created' in dir(model):
            data = data_query.filter(created__year=date)

        elif 'date' in dir(model):
            data = data_query.filter(date__year=date)

        return data

    @staticmethod
    def filter_by_month(date, data_query, model):
        """
        Filtrování dat podle měsíce.

        :param date: Měsíc
        :param data_query: Queryset
        :param model: Django model
        :return: queryset
        """
        data = None
        if 'created' in dir(model):
            data = data_query.filter(created__month=date)

        elif 'date' in dir(model):
            data = data_query.filter(date__month=date)

        return data

    @staticmethod
    def filter_by_day(date, data_query, model):
        """
        Filtrování dat podle dne.

        :param date: Den
        :param data_query: Queryset
        :param model: Django model
        :return: Filtrovaný queryset
        """
        data = None
        if 'created' in dir(model):
            data = data_query.filter(created__day=date)

        elif 'date' in dir(model):
            data = data_query.filter(date__day=date)

        return data
