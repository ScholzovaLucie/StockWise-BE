import pytest
from rest_framework import status
from warehouse.models import Warehouse
from position.models import Position
from box.models import Box


# Fixture vytvoří dvě pozice v rámci jednoho skladu a jednu krabici na první pozici
@pytest.fixture
def sample_positions(db):
    warehouse = Warehouse.objects.create(name="Main Warehouse")
    p1 = Position.objects.create(code="A01", warehouse=warehouse)
    p2 = Position.objects.create(code="B02", warehouse=warehouse)
    Box.objects.create(ean="EAN123456", position=p1)
    return p1, p2


@pytest.mark.django_db
class TestPositionViewSet:

    # Ověřuje, že volání bez parametru 'q' vrátí chybu
    def test_search_requires_query(self, authenticated_client):
        response = authenticated_client.get("/api/positions/search/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["detail"] == "Query parameter 'q' is required."

    # Vyhledání pozice podle kódu pozice
    def test_search_by_code(self, authenticated_client, sample_positions):
        response = authenticated_client.get("/api/positions/search/?q=A01")
        assert response.status_code == status.HTTP_200_OK
        assert any(p["code"] == "A01" for p in response.data.get("results", []))

    # Vyhledání pozic podle názvu skladu (funguje, pokud backend implementuje hledání i podle `warehouse__name`)
    def test_search_by_warehouse_name(self, authenticated_client, sample_positions):
        response = authenticated_client.get("/api/positions/search/?q=Main Warehouse")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2  # Předpoklad: není stránkované nebo vrací list

    # Vyhledání pozice podle EAN krabice, která se nachází na dané pozici
    def test_search_by_box_ean(self, authenticated_client, sample_positions):
        response = authenticated_client.get("/api/positions/search/?q=EAN123456")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data.get('results')) == 1
        assert response.data.get('results')[0]["code"] == "A01"

    # Vyhledávání podle více termínů – např. více kódů pozic oddělených čárkou
    def test_search_multiple_terms(self, authenticated_client, sample_positions):
        response = authenticated_client.get("/api/positions/search/?q=A01,B02")
        assert response.status_code == status.HTTP_200_OK
        codes = [p["code"] for p in response.data.get('results', [])]
        assert "A01" in codes and "B02" in codes

    # Ověřuje stránkování výsledků pomocí `page_size`
    def test_search_with_pagination(self, authenticated_client, sample_positions):
        response = authenticated_client.get("/api/positions/search/?q=A01,B02&page_size=1")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 1