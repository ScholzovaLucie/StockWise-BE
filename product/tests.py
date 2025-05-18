import pytest

from batch.models import Batch
from group.models import Group
from operation.models import Operation
from product.models import Product
from user.models import User


# Vytvoří testovacího uživatele s jedním klientem
@pytest.fixture
def product_user(client_factory):
    client = client_factory()
    user = User.objects.create(email="prod@example.com", password="pass")
    user.client.add(client)
    return user


# Vytvoří dva produkty pro zadaného klienta
@pytest.fixture
def sample_products(product_user):
    client = product_user.client.first()
    return [
        Product.objects.create(name="Testovací produkt", sku="SKU123", client=client),
        Product.objects.create(name="Další produkt", sku="SKU456", client=client, description="Popis testu")
    ]


@pytest.mark.django_db
class TestProductViewSet:

    # Ověřuje, že vyhledávání bez dotazu `q` vrátí chybu
    def test_search_requires_query(self, authenticated_client):
        res = authenticated_client.get("/api/products/search/")
        assert res.status_code == 400
        assert res.data["detail"] == "Query parameter 'q' is required."

    # Vyhledávání podle jednoho slova
    def test_search_single_term(self, authenticated_client, sample_products):
        res = authenticated_client.get("/api/products/search/?q=Test")
        assert res.status_code == 200
        assert any("Testovací produkt" in p["name"] for p in res.data["results"])

    # Vyhledávání podle více termínů
    def test_search_multiple_terms(self, authenticated_client, sample_products):
        res = authenticated_client.get("/api/products/search/?q=Test,Popis")
        assert res.status_code == 200
        assert len(res.data["results"]) >= 1

    # Vyhledávání s omezením na konkrétního klienta
    def test_search_with_client_id(self, authenticated_client, sample_products, product_user):
        client_id = product_user.client.first().id
        res = authenticated_client.get(f"/api/products/search/?q=SKU123&client_id={client_id}")
        assert res.status_code == 200
        assert len(res.data["results"]) == 1

    # Ověřuje, že endpoint vrací pouze produkty pro daného klienta
    def test_by_client(self, authenticated_client, sample_products, product_user):
        client_id = product_user.client.first().id
        res = authenticated_client.get(f"/api/products/by-client/{client_id}/")
        assert res.status_code == 200
        assert all(p["name"] in [sp.name for sp in sample_products] for p in res.data)

    # Ověřuje, že nový produkt má nulový skladový stav
    def test_get_product_stock_zero_by_default(self, authenticated_client, sample_products):
        product = sample_products[0]
        res = authenticated_client.get(f"/api/products/{product.id}/stock/")
        assert res.status_code == 200
        assert res.data["available"] == 0

    # Ověřuje, že po dokončené příjmové operaci se aktualizuje množství produktu
    def test_product_amount_after_completed_in_operation(self, product_user):
        client = product_user.client.first()
        product = Product.objects.create(name="Auto produkt", sku="AUTO123", client=client)

        operation = Operation.objects.create(
            number="OP-TEST-1",
            type="IN",
            status="COMPLETED",
            user=product_user,
            client=client
        )

        batch = Batch.objects.create(product=product, batch_number="BATCH-TEST")
        group = Group.objects.create(batch=batch, quantity=7)
        operation.groups.add(group)

        product.refresh_from_db()
        assert product.amount == 7

    # Ověřuje, že dotaz na neexistující produkt vrátí správnou chybu
    def test_get_product_stock_not_found(self, authenticated_client):
        res = authenticated_client.get(f"/api/products/999999/stock/")
        assert res.status_code == 404
        assert res.data["error"] == "Produkt nebyl nalezen"

    # Ověřuje, že lze vytvořit jeden produkt pomocí endpointu `bulk_create`
    def test_bulk_create_single(self, authenticated_client, product_user):
        client_id = product_user.client.first().id
        res = authenticated_client.post("/api/products/bulk_create/", {
            "name": "Bulk produkt",
            "sku": "BULK-1",
            "client_id": client_id
        }, format="json")
        assert res.status_code == 201
        assert res.data["name"] == "Bulk produkt"

    # Ověřuje, že lze vytvořit více produktů najednou přes `bulk_create`
    def test_bulk_create_multiple(self, authenticated_client, product_user):
        client_id = product_user.client.first().id
        res = authenticated_client.post("/api/products/bulk_create/", [
            {"name": "Bulk A", "sku": "BULK-A", "client_id": client_id},
            {"name": "Bulk B", "sku": "BULK-B", "client_id": client_id}
        ], format="json")
        assert res.status_code == 201
        assert isinstance(res.data, list)
        assert len(res.data) == 2