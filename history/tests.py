import pytest
from rest_framework import status
from history.models import History
from user.models import User


# Fixture pro vytvoření uživatele s přiřazeným klientem
@pytest.fixture
def history_user(client_factory):
    client = client_factory()
    user = User.objects.create(email="history@example.com", password="pass")
    user.client.add(client)
    return user


# Fixture pro autentizovaného klienta jako history_user
@pytest.fixture
def authenticated_history_client(api_client, history_user):
    api_client.force_authenticate(user=history_user)
    return api_client


# Fixture pro vytvoření několika záznamů historie s různými typy
@pytest.fixture
def sample_history_data(db, history_user):
    History.objects.create(description="Záznam operace", type="operation", related_id=1, user=history_user)
    History.objects.create(description="Záznam produktu", type="product", related_id=2, user=history_user)
    History.objects.create(description="Pozice změněna", type="position", related_id=3, user=history_user)
    History.objects.create(description="Batch přiřazen", type="batch", related_id=4, user=history_user)
    History.objects.create(description="Skupina odebrána", type="group", related_id=5, user=history_user)


@pytest.mark.django_db
class TestHistorySearch:
    # Testuje, že endpoint vrací 400, pokud chybí parametr `q`
    def test_search_requires_query(self, authenticated_history_client):
        response = authenticated_history_client.get("/api/history/search/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Query parameter 'q' is required."

    # Testuje hledání záznamu podle výskytu výrazu v popisu
    def test_search_by_description(self, authenticated_history_client, sample_history_data):
        response = authenticated_history_client.get("/api/history/search/?q=operace")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0
        assert any("operace" in h["description"] for h in response.data["results"])

    # Testuje hledání podle více výrazů (oddělených čárkou)
    def test_search_multiple_terms(self, authenticated_history_client, sample_history_data):
        response = authenticated_history_client.get("/api/history/search/?q=produkt,pozice")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0


@pytest.mark.django_db
class TestHistoryTypeEndpoints:

    # Test parametrizovaného výpisu historie podle typu (operation, product, ...)
    @pytest.mark.parametrize("endpoint,type_value", [
        ("operation", "operation"),
        ("product", "product"),
        ("position", "position"),
        ("batch", "batch"),
        ("group", "group"),
    ])
    def test_type_history(self, authenticated_history_client, sample_history_data, endpoint, type_value):
        response = authenticated_history_client.get(f"/api/history/{endpoint}/")
        assert response.status_code == status.HTTP_200_OK
        assert all(h["type"] == type_value for h in response.data["results"])

    # Testuje, že endpoint filtruje historii podle `related_id`
    def test_type_history_with_related_id(self, authenticated_history_client, sample_history_data):
        response = authenticated_history_client.get("/api/history/group/?related_id=5")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["related_id"] == 5