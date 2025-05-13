import pytest
from rest_framework import status

from operation.services.operation_service import create_operation
from product.models import Product
from user.models import User
from client.models import Client
from operation.models import Operation


@pytest.fixture
def operation_user(client_factory):
    client = client_factory()
    user = User.objects.create(email="opuser@example.com", password="pass")
    user.client.add(client)
    return user


@pytest.fixture
def authenticated_operation_client(api_client, operation_user):
    api_client.force_authenticate(user=operation_user)
    return api_client


@pytest.fixture
def sample_operation(db, operation_user):
    client = operation_user.client.first()
    return Operation.objects.create(
        number="OP001",
        type="IN",
        status="CREATED",
        client=client,
        user=operation_user
    )


@pytest.mark.django_db
class TestOperationViewSet:

    def test_list_operations(self, authenticated_operation_client, sample_operation):
        response = authenticated_operation_client.get("/api/operations/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data['results']
        assert any(op['number'] == "OP001" for op in response.data['results'])

    def test_get_operation_detail(self, authenticated_operation_client, sample_operation):
        response = authenticated_operation_client.get(f"/api/operations/{sample_operation.id}/")
        assert response.status_code == 200
        assert response.data['number'] == "OP001"

    def test_get_types(self, authenticated_operation_client):
        response = authenticated_operation_client.get("/api/operations/types/")
        assert response.status_code == 200
        assert "IN" in response.data["data"]

    def test_get_statuses(self, authenticated_operation_client):
        response = authenticated_operation_client.get("/api/operations/statuses/")
        assert response.status_code == 200
        assert "CREATED" in response.data["data"]

    def test_search_operations(self, authenticated_operation_client, sample_operation):
        response = authenticated_operation_client.get("/api/operations/search/?q=OP001")
        assert response.status_code == 200
        assert any(op['id'] == sample_operation.id for op in response.data['results'])

