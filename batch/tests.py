import pytest
import uuid
from rest_framework import status

from batch.models import Batch
from product.models import Product


@pytest.fixture
def batch_factory(db, client_factory):
    def create_batch(**kwargs):
        client = kwargs.pop('client', client_factory())
        product = kwargs.pop('product', Product.objects.create(
            name=kwargs.pop('product__name', 'Test Product'),
            sku=kwargs.pop('product__sku', f'TESTSKU-{uuid.uuid4()}'),
            client=client
        ))
        defaults = {
            'batch_number': kwargs.pop('batch_number', 'TESTBATCH'),
            'product': product,
            'expiration_date': '2099-12-31',
        }
        defaults.update(kwargs)
        return Batch.objects.create(**defaults)
    return create_batch


@pytest.mark.django_db
class TestBatchViewSetList:
    @pytest.mark.django_db
    def test_list_batches_for_user_client(self, authenticated_client, batch_factory, user_with_client):
        client = user_with_client.client.first()
        batch = batch_factory(client=client)

        response = authenticated_client.get('/api/batches/')

        assert response.status_code == status.HTTP_200_OK
        assert any(b['id'] == batch.id for b in response.data.get('results'))

    @pytest.mark.django_db
    def test_list_batches_filters_by_client_id(self, authenticated_client, batch_factory, client_factory):
        other_client = client_factory()
        batch = batch_factory(client=other_client)

        response = authenticated_client.get(f'/api/batches/?client_id={other_client.id}')

        assert response.status_code == status.HTTP_200_OK
        assert all(b['product'] == batch.product for b in response.data.get('results'))

    def test_search_requires_query_param(self, authenticated_client):
        response = authenticated_client.get('/api/batches/search/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['detail'] == "Query parameter 'q' is required."

    def test_search_batches_by_single_term(self, authenticated_client, batch_factory):
        batch = batch_factory(batch_number="ABC123")

        response = authenticated_client.get('/api/batches/search/?q=ABC')

        assert response.status_code == status.HTTP_200_OK
        assert any(b['id'] == batch.id for b in response.data.get('results'))

    def test_search_batches_by_multiple_terms(self, authenticated_client, batch_factory):
        batch1 = batch_factory(batch_number="FIRST123")
        batch2 = batch_factory(product__name="SecondBatch")

        response = authenticated_client.get('/api/batches/search/?q=FIRST,Second')

        assert response.status_code == status.HTTP_200_OK
        batch_ids = [b['id'] for b in response.data.get('results', [])]
        assert batch1.id in batch_ids
        assert batch2.id in batch_ids

    def test_search_batches_filters_by_client_id(self, authenticated_client, batch_factory, client_factory):
        other_client = client_factory()
        batch = batch_factory(client=other_client, batch_number="XYZ789")

        response = authenticated_client.get(f'/api/batches/search/?q=XYZ&clientId={other_client.id}')

        assert response.status_code == status.HTTP_200_OK
        assert any(b['id'] == batch.id for b in response.data.get('results'))