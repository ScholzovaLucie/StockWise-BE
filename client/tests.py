import pytest
from rest_framework import status
from client.models import Client
from user.models import User


# Fixture pro vytvoření uživatele, který má přiřazené dva klienty
@pytest.fixture
def user_with_clients(db):
    user = User.objects.create(email="clientuser@example.com", password="pass")
    client1 = Client.objects.create(name="TestClient A", email="a@example.com")
    client2 = Client.objects.create(name="TestClient B", email="b@example.com")
    user.client.add(client1, client2)
    return user

# Fixture pro autentizovaného klienta přihlášeného jako uživatel s klienty
@pytest.fixture
def authenticated_client_user(api_client, user_with_clients):
    api_client.force_authenticate(user=user_with_clients)
    return api_client


@pytest.mark.django_db
class TestClientViewSet:

    # Testuje, že se vrátí pouze klienti přiřazení uživateli
    def test_get_clients_only_assigned(self, authenticated_client_user):
        response = authenticated_client_user.get("/api/clients/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    # Testuje, že s parametrem `?all=true` se vrátí všichni klienti (i nepřiřazení)
    def test_get_all_clients(self, authenticated_client_user, user_with_clients):
        client = Client.objects.create(name="Unrelated", email="x@external.com")
        user_with_clients.client.add(client)
        user_with_clients.save()
        response = authenticated_client_user.get("/api/clients/?all=true")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get('results')) >= 3

    # Testuje, že klienti lze filtrovat podle `client_id`
    def test_get_client_by_id(self, authenticated_client_user, user_with_clients):
        target_client = user_with_clients.client.first()
        response = authenticated_client_user.get(f"/api/clients/?client_id={target_client.id}")
        assert response.status_code == status.HTTP_200_OK
        assert all(client["id"] == target_client.id for client in response.data.get('results'))

    # Testuje, že chybějící `q` parametr ve vyhledávání vrací chybu 400
    def test_search_requires_q(self, authenticated_client_user):
        response = authenticated_client_user.get("/api/clients/search/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Query parameter 'q' is required."

    # Testuje vyhledávání podle jednoho výrazu
    def test_search_single_term(self, authenticated_client_user):
        Client.objects.create(name="Alpha Client", email="alpha@example.com")
        response = authenticated_client_user.get("/api/clients/search/?q=alpha")
        assert response.status_code == status.HTTP_200_OK
        assert any("Alpha Client" in c["name"] for c in response.data)

    # Testuje vyhledávání podle více výrazů (oddělených čárkou)
    def test_search_multiple_terms(self, authenticated_client_user):
        Client.objects.create(name="Bravo", email="b1@example.com")
        Client.objects.create(name="Charlie", email="c2@example.com")
        response = authenticated_client_user.get("/api/clients/search/?q=bravo,charlie")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2