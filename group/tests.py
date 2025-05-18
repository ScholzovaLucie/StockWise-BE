import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.urls import reverse

from operation.models import Operation
from user.models import User
from client.models import Client
from group.models import Group
from batch.models import Batch
from product.models import Product
from box.models import Box


# Fixture pro základního neautentizovaného API klienta
@pytest.fixture
def api_client():
    return APIClient()


# Factory fixture pro vytváření klientů
@pytest.fixture
def client_factory(db):
    def create_client(**kwargs):
        return Client.objects.create(name="Test Client", **kwargs)
    return create_client


# Fixture pro uživatele, který má přiřazeného jednoho klienta
@pytest.fixture
def group_user(client_factory):
    client = client_factory()
    user = User.objects.create(email='groupuser@example.com', password='test')
    user.client.add(client)
    return user


# Fixture pro autentizovaného API klienta přihlášeného jako uživatel s klientem
@pytest.fixture
def authenticated_group_client(api_client, group_user):
    api_client.force_authenticate(user=group_user)
    return api_client


# Fixture pro vytvoření group se všemi vazbami (product, batch, box)
@pytest.fixture
def group_with_relations(db, client_factory):
    client = client_factory()
    product = Product.objects.create(name="TestProduct", sku="TP123", client=client)
    batch = Batch.objects.create(batch_number="B123", product=product)
    box = Box.objects.create(ean="BOX-001")
    group = Group.objects.create(batch=batch, box=box, quantity=1)
    return group


@pytest.mark.django_db
class TestGroupViewSet:

    # Testuje, že se správně aktualizuje množství produktu při přidání/odebrání group
    def test_product_amount_updates(self, client_factory):
        client = client_factory()
        product = Product.objects.create(name="Test Produkt", sku="TEST123", client=client)

        assert product.amount == 0

        batch = Batch.objects.create(product=product, batch_number="BATCH001")
        group = Group.objects.create(batch=batch, quantity=10)
        op = Operation.objects.create(type='IN', number="test_op", client=client, status="COMPLETED")
        op.groups.add(group)
        op.save()

        product.refresh_from_db()
        assert product.amount == 10  # Množství se má zvýšit

        Group.objects.filter(batch=batch).delete()
        product.refresh_from_db()
        assert product.amount == 0  # Množství se má snížit na nulu

    # Testuje, že přihlášený uživatel může získat seznam group
    def test_list_groups_authenticated(self, authenticated_group_client, group_with_relations):
        response = authenticated_group_client.get("/api/groups/")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data.get('results'), list)

    # Testuje, že vyhledávání bez parametru `q` vrací chybu
    def test_search_requires_query_param(self, authenticated_group_client):
        response = authenticated_group_client.get("/api/groups/search/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Query parameter 'q' is required."

    # Testuje vyhledávání podle jednoho výrazu (např. SKU)
    def test_search_by_single_term(self, authenticated_group_client, group_with_relations):
        response = authenticated_group_client.get("/api/groups/search/?q=TP123")
        assert response.status_code == status.HTTP_200_OK
        assert any("id" in g for g in response.data)

    # Testuje vyhledávání podle více výrazů (SKU, batch_number, EAN)
    def test_search_by_multiple_terms(self, authenticated_group_client, group_with_relations):
        response = authenticated_group_client.get("/api/groups/search/?q=TP123,B123,BOX-001")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert any("id" in g for g in response.data)

    # Testuje vyhledávání group s omezením podle konkrétního klienta
    def test_search_with_client_id(self, authenticated_group_client, group_with_relations):
        client_id = group_with_relations.batch.product.client.id
        response = authenticated_group_client.get(f"/api/groups/search/?q=TP123&clientId={client_id}")
        assert response.status_code == status.HTTP_200_OK
        assert any("id" in g for g in response.data)

    # Testuje úspěšné odstranění boxu z group (custom endpoint)
    def test_remove_from_box_success(self, authenticated_group_client, group_with_relations):
        group_id = group_with_relations.id
        assert group_with_relations.box is not None
        response = authenticated_group_client.post(f"/api/groups/{group_id}/remove_from_box/")
        assert response.status_code == status.HTTP_200_OK
        group_with_relations.refresh_from_db()
        assert group_with_relations.box is None
        assert response.data["message"].startswith("Produkt")

    # Testuje volání `remove_from_box` s neexistujícím ID group – očekává se 404
    def test_remove_from_box_not_found(self, authenticated_group_client):
        response = authenticated_group_client.post("/api/groups/99999/remove_from_box/")
        assert response.status_code == status.HTTP_404_NOT_FOUND