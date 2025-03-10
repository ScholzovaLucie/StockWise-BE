from datetime import datetime, timedelta

from django.http import JsonResponse

from box.models import Box
from client.models import Client
from group.models import Group
from operation.models import Operation
from position.models import Position
from product.models import Product
from product.serializers import ProductSerializer


def get_function(function_name):
    available_functions = {
        'getItems': (AssistantDataCreator().get_data, Product, ProductSerializer),
    }
    return available_functions[function_name]


class AssistantDataCreator(object):
    def get_data(self, call_id, parameters, client_id, model, serializer):
        data_query = model.objects.all()

        if 'client_id' in dir(model) and client_id:
            data_query = data_query.filter(client_id=client_id)

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

    def get_operation_items(self, call_id, parameters, client_id, model, serializer):
        data_query = model.objects.all()

        if client_id:
            data_query = data_query.filter(client_id=client_id)

        if parameters.get('number') is None:
            return None

        data_query = data_query.filter(number=parameters.get('number')).first().items.all()

        data = list(data_query.values(
            'batch__product__id',
            'batch__product__sku',
            'batch__product__name',
            'batch__product__description',
            'batch__product__amount',
        ))
        data_bytes = JsonResponse(data, safe=False).content

        outputs = {
            data_bytes.decode("utf-8")
        }
        return {
            'tool_call_id': call_id,
            'output': str(outputs)
        }

    def get_hu_of_item(self, call_id, parameters, client_id, model, serializer):
        data_query = model.objects.all()
        hus = {}

        if client_id:
            data_query = data_query.filter(client_id=client_id)

        products = self.filter_item(parameters, data_query)

        for data in products:
            groups = Group.objects.filter(batch__product=data)
            hus[data.ean] = []
            for group in groups:
                query = Box.objects.filter(id=group.box.id, out=parameters.get('out'))
                data_serialized = serializer(query, many=True).data[0] if query.count() != 0 else None
                data_bytes = JsonResponse(data_serialized, safe=False).content
                hus[data.ean].append(data_bytes.decode("utf-8"))

        return {
            'tool_call_id': call_id,
            'output': str(hus)
        }

    def get_position_of_item(self, call_id, parameters, client_id, model, serializer):
        data_query = model.objects.all()
        hus = {}

        if client_id:
            data_query = data_query.filter(client_id=client_id)

        products = self.filter_item(parameters, data_query)

        for data in products:
            groups = Group.objects.filter(batch__product=data)
            hus[data.ean] = []
            for group in groups:
                query = Position.objects.filter(id=group.box.position.id)
                data_serialized = serializer(query, many=True).data[0] if query.count() != 0 else None
                data_bytes = JsonResponse(data_serialized, safe=False).content
                hus[data.ean].append(data_bytes.decode("utf-8"))

        return {
            'tool_call_id': call_id,
            'output': str(hus)
        }

    def get_count_of_items_operation(self, call_id, parameters, client_id, model, serializer):
        data_query = model.objects.all()
        all_operations = {}

        if client_id:
            data_query = data_query.filter(client_id=client_id)

        data_query = self.filter_item(parameters, data_query)

        for product in data_query:
            operations = Operation.objects.filter(groups__batch__product=product).count()
            all_operations[product.code] = operations

        return {
            'tool_call_id': call_id,
            'output': str(all_operations)
        }

    @staticmethod
    def get_position_by_client(call_id, parameters, client_id, model, serializer):
        count = 0

        client_company = parameters.get('client_company', None)
        client = Client.objects.get(company=client_company)

        if client:
            groups = Group.objects.filter(batch__product__client__id=client.id)
            count = groups.filter(box__position__isnull=False).count()

        return {
            'tool_call_id': call_id,
            'output': str(count)
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

    def get_items_by_expiration_and_date(self, call_id, parameters, client_id, model, serializer):
        expired = parameters.get('expired')
        date = parameters.get('date')

        # Kombinace dotazů pro Batch a HUItem
        data_query = model.objects.prefetch_related('batch_set__huitem_set').all()

        data = {}

        for item in data_query:
            for batch in item.batch_set.all():
                huitem = batch.huitem_set.filter(out=False).first()

                if huitem:
                    module = huitem.client.import_specific('batchCodesCodifications')
                    if module is None:
                        continue

                    made = module.expiration_from_batch(batch.id, datetime.now().date(), brand=batch.item.brand)
                    if made:
                        expiration = made.get('expiration') or (made.get('date') + timedelta(
                            days=huitem.batch.item.usability)) if huitem.batch.item.usability > 0 else made.get('date')

                        if batch.item.min_usability > 0:
                            try:
                                is_expired = (expiration - datetime.now()).days <= batch.item.min_usability
                            except Exception:
                                is_expired = False
                        else:
                            is_expired = expiration < datetime.now().date()

                        if type(expiration) == datetime:
                            expiration = expiration.date()

                        item_data = {
                            'expiration': expiration.strftime("%Y-%m-%d"),
                            'is_expired': is_expired
                        }
                    else:
                        item_data = {
                            'expiration': None,
                            'is_expired': False
                        }

                    if not date and item_data['is_expired'] and expired:
                        data[item.code][batch.batch] = item_data
                    if not date and not expired and not item_data['is_expired']:
                        data[item.code][batch.batch] = item_data
                    if date and not item_data['is_expired']:
                        if item_data['expiration'] <= date:
                            data[item.code][batch.batch] = item_data

        return {
            'tool_call_id': call_id,
            'output': str(data)
        }




