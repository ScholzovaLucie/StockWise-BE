import pytest
import uuid
from rest_framework import status
from rest_framework.test import APIClient

from box.models import Box
from client.models import Client
from product.models import Product
from user.models import User
from group.models import Group
from batch.models import Batch
from position.models import Position
from warehouse.models import Warehouse


@pytest.fixture
def box_with_product(db, client_factory):
    client = client_factory()
    product = Product.objects.create(name='BoxProduct', sku=f'SKU-{uuid.uuid4()}', client=client)
    batch = Batch.objects.create(batch_number='BATCH1', product=product, expiration_date='2099-12-31')
    warehouse = Warehouse.objects.create(name="Testovací sklad")
    position = Position.objects.create(code='POS123', warehouse=warehouse)
    box = Box.objects.create(ean='BOX123456789', position=position)
    Group.objects.create(box=box, batch=batch, quantity=5)
    return box


@pytest.mark.django_db
class TestBoxViewSetSearch:

    def test_search_requires_query_param(self, authenticated_client):
        response = authenticated_client.get('/api/boxes/search/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['detail'] == "Query parameter 'q' is required."

    def test_search_by_ean(self, authenticated_client):
        box = Box.objects.create(ean='EAN123456789')
        response = authenticated_client.get('/api/boxes/search/?q=EAN123')
        assert response.status_code == status.HTTP_200_OK
        assert any(b['id'] == box.id for b in response.data.get('results', []))

    def test_search_by_multiple_terms(self, authenticated_client):
        warehouse = Warehouse.objects.create(name="Sklad 1")
        box1 = Box.objects.create(ean='ABC123')
        position = Position.objects.create(code='DEF456', warehouse=warehouse)
        box2 = Box.objects.create(ean='ZZZ999', position=position)

        response = authenticated_client.get('/api/boxes/search/?q=ABC,DEF')

        assert response.status_code == status.HTTP_200_OK
        box_ids = [b['id'] for b in response.data['results']]
        assert box1.id in box_ids
        assert box2.id in box_ids


@pytest.mark.django_db
class TestBoxViewSetProducts:

    def test_get_products_in_box(self, authenticated_client, box_with_product):
        response = authenticated_client.get(f'/api/boxes/{box_with_product.id}/products/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['name'] == 'BoxProduct'
        assert response.data[0]['quantity'] == 5