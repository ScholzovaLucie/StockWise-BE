import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import timedelta
from user.models import User
from client.models import Client
from product.models import Product
from batch.models import Batch
from group.models import Group
from operation.models import Operation
from history.models import History


@pytest.fixture
def authenticated_client_with_data(db):
    client = Client.objects.create(name="TestClient")
    user = User.objects.create(email="user@example.com", password="testpass")
    user.client.add(client)

    product = Product.objects.create(name="TestProduct", sku="SKU123", client=client, amount_cached=5)
    batch = Batch.objects.create(batch_number="BATCH123", product=product, expiration_date=timezone.now().date() + timedelta(days=15))
    operation = Operation.objects.create(client=client, type="IN", status="COMPLETED", number="OP123", user=user)
    group = Group.objects.create(batch=batch, quantity=5)
    operation.groups.add(group)

    History.objects.create(type="product", related_id=product.id, description="Product added")
    History.objects.create(type="operation", related_id=operation.id, description="Operation done")
    History.objects.create(type="batch", related_id=batch.id, description="Batch created")
    History.objects.create(type="group", related_id=group.id, description="Group linked")

    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client, client, user


@pytest.mark.django_db
class TestDashboardViews:

    def test_dashboard_overview(self, authenticated_client_with_data):
        api_client, client, _ = authenticated_client_with_data
        res = api_client.get(f"/api/dashboard/overview/?clientId={client.id}")
        assert res.status_code == status.HTTP_200_OK
        assert isinstance(res.data["totalItems"], int)

    def test_dashboard_low_stock(self, authenticated_client_with_data):
        api_client, client, _ = authenticated_client_with_data
        res = api_client.get(f"/api/dashboard/low_stock/?clientId={client.id}")
        assert res.status_code == status.HTTP_200_OK

    def test_dashboard_recent_activity(self, authenticated_client_with_data):
        api_client, client, _ = authenticated_client_with_data
        res = api_client.get(f"/api/dashboard/recent_activity/?clientId={client.id}")
        assert res.status_code == status.HTTP_200_OK

    def test_dashboard_alerts(self, authenticated_client_with_data):
        api_client, client, _ = authenticated_client_with_data
        res = api_client.get(f"/api/dashboard/alerts/?clientId={client.id}")
        assert res.status_code == status.HTTP_200_OK

    def test_dashboard_active_operations(self, authenticated_client_with_data):
        api_client, client, _ = authenticated_client_with_data
        res = api_client.get(f"/api/dashboard/active_operations/?clientId={client.id}")
        assert res.status_code == status.HTTP_200_OK

    def test_dashboard_stats(self, authenticated_client_with_data):
        api_client, client, _ = authenticated_client_with_data
        res = api_client.get(f"/api/dashboard/stats/?clientId={client.id}")
        assert res.status_code == status.HTTP_200_OK

    def test_dashboard_efficiency(self, authenticated_client_with_data):
        api_client, client, _ = authenticated_client_with_data
        res = api_client.get(f"/api/dashboard/efficiency/?clientId={client.id}")
        assert res.status_code == status.HTTP_200_OK

    def test_dashboard_extended_stats(self, authenticated_client_with_data):
        api_client, client, _ = authenticated_client_with_data
        res = api_client.get(f"/api/dashboard/extended_stats/?clientId={client.id}")
        assert res.status_code == status.HTTP_200_OK

    def test_unauthenticated_request_returns_403(self):
        client = APIClient()
        res = client.get("/api/dashboard/overview/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_client_id_returns_empty_data(self, authenticated_client_with_data):
        api_client, _, _ = authenticated_client_with_data
        res = api_client.get("/api/dashboard/overview/?clientId=9999")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["totalItems"] == 0

    def test_invalid_date_format_in_recent_activity(self, authenticated_client_with_data):
        api_client, client, _ = authenticated_client_with_data
        res = api_client.get(f"/api/dashboard/recent_activity/?clientId={client.id}&filters[from_date]=invalid-date")
        assert res.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR or res.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_required_params_fallback_to_default(self, authenticated_client_with_data):
        api_client, _, _ = authenticated_client_with_data
        res = api_client.get("/api/dashboard/recent_activity/")
        assert res.status_code == status.HTTP_200_OK
        assert "chart" in res.data

    def test_efficiency_with_no_operations(self, db):
        client = Client.objects.create(name="EmptyClient")
        user = User.objects.create(email="empty@example.com", password="pass")
        user.client.add(client)
        api_client = APIClient()
        api_client.force_authenticate(user=user)
        res = api_client.get(f"/api/dashboard/efficiency/?clientId={client.id}")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["efficiency"] == 0