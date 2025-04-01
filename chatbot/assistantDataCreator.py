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
from operation.serializers import OperationSerializer, OutOperationSerializer, InOperationSerializer, \
    OutOperationBulkSerializer, InOperationBulkSerializer
from position.models import Position
from position.serializers import PositionSerializer, PositionBulkSerializer
from product.models import Product
from product.serializers import ProductSerializer, ProductBulkSerializer
from user.models import User
from user.serializers import UserSerializer, UserBulkSerializer
from warehouse.models import Warehouse
from warehouse.serializers import WarehouseSerializer, WarehouseBulkSerializer

def with_type(func, history_type):
    return lambda call_id, parameters, client_id, model, serializer, user: \
        func(call_id, parameters, client_id, model, serializer, user, history_type)


def get_function(function_name):
    available_functions = {
        # Get
        'getBatches': (AssistantDataCreator().get_data, Batch, BatchSerializer),
        'getClients': (AssistantDataCreator().get_data, Client, ClientSerializer),
        'getGroups': (AssistantDataCreator().get_data, Group, GroupSerializer),
        'getOperations': (AssistantDataCreator().get_data, Operation, OperationSerializer),
        'getPositions': (AssistantDataCreator().get_data, Position, PositionSerializer),
        'getProducts': (AssistantDataCreator().get_data, Product, ProductSerializer),
        'getUsers': (AssistantDataCreator().get_data, User, UserSerializer),
        'getWarehouses': (AssistantDataCreator().get_data, Warehouse, WarehouseSerializer),
        'getOperationStatuses': (AssistantDataCreator().getOperationStatuses, Operation, OperationSerializer),
        'getHistory': (AssistantDataCreator().get_history_data, History, HistorySerializer),
        'getOperationHistory': (with_type(AssistantDataCreator().get_specific_history_data, 'operation'), History, HistorySerializer),
        'getProductHistory': (with_type(AssistantDataCreator().get_specific_history_data, 'product'), History, HistorySerializer),
        'getBatchHistory': (with_type(AssistantDataCreator().get_specific_history_data, 'batch'), History, HistorySerializer),
        'getGroupHistory': (with_type(AssistantDataCreator().get_specific_history_data, 'group'), History, HistorySerializer),
        'getPositionHistory': (with_type(AssistantDataCreator().get_specific_history_data, 'position'), History, HistorySerializer),

        # Post
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
        'createOutOperations': (AssistantDataCreator().bulk_create_data, Operation, OutOperationBulkSerializer),
        'createInOperations': (AssistantDataCreator().bulk_create_data, Operation, InOperationBulkSerializer),
        'createPositions': (AssistantDataCreator().bulk_create_data, Position, PositionBulkSerializer),
        'createUsers': (AssistantDataCreator().bulk_create_data, User, UserBulkSerializer),

        # Update
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
        data_query = model.objects.all()

        if 'type' in parameters:
            data_query = data_query.filter(type=parameters['type'])

        if 'from_timestamp' in parameters:
            data_query = data_query.filter(timestamp__gte=parameters['from_timestamp'])
        if 'to_timestamp' in parameters:
            data_query = data_query.filter(timestamp__lte=parameters['to_timestamp'])

        return self.format_data(HistorySerializer, data_query, call_id)

    def get_specific_history_data(self, call_id, parameters, client_id, model, serializer, user, history_type):
        parameters['type'] = history_type
        return self.get_history_data(call_id, parameters, client_id, model, serializer, user)

    def get_data(self, call_id, parameters, client_id, model, serializer, user):
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

        filter_params = [
            'code',
            'ean',
        ]
        for param in filter_params:
            if parameters.get(param) is not None:
                if param == 'employee_company':
                    data_query = self.filter_by_name(parameters.get(param), data_query)

                elif param == 'client_company':
                    client = Client.objects.get(company=parameters.get(param))
                    if client is not None:
                        data_query = data_query.filter(client_id=client.id)

                elif param == 'created_by_month':
                    data_query = self.filter_by_month(parameters.get(param), data_query, model)

                elif param == 'created_by_year':
                    data_query = self.filter_by_year(parameters.get(param), data_query, model)

                elif param == 'created_by_day':
                    data_query = self.filter_by_day(parameters.get(param), data_query, model)

                else:
                    data_query = data_query.filter(**{param: parameters.get(param)})

        if parameters.get('onlyCount'):
            count_of_data_query = data_query.count()
            return {
                        'tool_call_id': call_id,
                        'output': str(count_of_data_query)
                    }

        return self.format_data(serializer, data_query, call_id)

    def update_data(self, call_id, parameters, client_id, model, serializer, user):
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

    def getOperationStatuses(self, call_id, parameters, client_id, model, serializer, user):
        return {
            'tool_call_id': call_id,
            'output': Operation.OPERATION_STATUS_CHOICES
        }


    @staticmethod
    def format_data(serializer, data_query, call_id):
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
    def filter_item(parameters, data_query):
        if parameters.get('code') or parameters.get('ean'):
            filter_param = parameters.get('code') or parameters.get('ean')
            data = data_query.filter(code=filter_param)
            if data.count() == 0:
                data = data_query.filter(ean=filter_param)

            return data

    @staticmethod
    def filter_by_name(name, data_query):
        name = name.split(' ')
        if len(name) == 1:
            data = data_query.filter(employee__last_name=name[0])
            if data.count() == 0:
                data = data_query.filter(employee__first_name=name[0])
        else:
            data = data_query.filter(employee__last_name=name[0], employee__first_name=name[1])
            if data.count() == 0:
                data = data_query.filter(employee__last_name=name[1], employee__first_name=name[0])

        return data

    @staticmethod
    def filter_by_year(date, data_query, model):
        data = None
        if 'created' in dir(model):
            data = data_query.filter(created__year=date)

        elif 'date' in dir(model):
            data = data_query.filter(date__year=date)

        return data

    @staticmethod
    def filter_by_month(date, data_query, model):
        data = None
        if 'created' in dir(model):
            data = data_query.filter(created__month=date)

        elif 'date' in dir(model):
            data = data_query.filter(date__month=date)

        return data

    @staticmethod
    def filter_by_day(date, data_query, model):
        data = None
        if 'created' in dir(model):
            data = data_query.filter(created__day=date)

        elif 'date' in dir(model):
            data = data_query.filter(date__day=date)

        return data
