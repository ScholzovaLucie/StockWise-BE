import pytest
from rest_framework.test import APIClient
from operation.models import Operation

@pytest.mark.django_db
class TestOperationViews:

    def test_create_out_operation_view(self, user):
        """
        Otestuje vytvoření nové výdejky.
        """
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post("/api/create_out_operation", {"description": "Testovací výdejka"})
        assert response.status_code == 201
        assert "operation_id" in response.data

    def test_create_in_operation_view(self, user):
        """
        Otestuje vytvoření nové příjemky.
        """
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post("/api/create_in_operation", {"description": "Testovací příjemka"})
        assert response.status_code == 201
        assert "operation_id" in response.data

    def test_add_group_to_out_operation_view(self, user, batch_factory, box_factory):
        """
        Otestuje přidání skupiny do výdejky.
        """
        client = APIClient()
        client.force_authenticate(user=user)

        operation = Operation.objects.create(type="OUT", status="CREATED", user=user)
        batch = batch_factory()
        box = box_factory()

        response = client.post(f"/api/add_group_to_out_operation/{operation.id}/", {
            "batch_id": batch.id,
            "box_id": box.id,
            "quantity": 5
        })
        assert response.status_code == 201
        assert "group_id" in response.data

    def test_process_out_operation_view(self, user, batch_factory, group_factory):
        """
        Otestuje zpracování výdejky.
        """
        client = APIClient()
        client.force_authenticate(user=user)

        operation = Operation.objects.create(type="OUT", status="IN_PROGRESS", user=user)
        batch = batch_factory()
        group = group_factory(batch=batch, quantity=10)
        operation.groups.add(group)

        response = client.post(f"/api/process_out_operation/{operation.id}/")
        assert response.status_code == 200
        assert "message" in response.data

    @pytest.mark.django_db
    def test_add_duplicate_batch_to_in_operation(user, product_factory, box_factory):
        """
        Otestuje, že nelze přidat stejnou šarži dvakrát do příjemky.
        """
        client = APIClient()
        client.force_authenticate(user=user)

        operation = Operation.objects.create(type="IN", status="CREATED", user=user)
        product = product_factory()
        box = box_factory()

        data = {
            "product_id": product.id,
            "batch_number": "BATCH123",
            "box_id": box.id,
            "quantity": 10
        }

        # První přidání by mělo projít
        response1 = client.post(f"/api/add_group_to_in_operation/{operation.id}/", data)
        assert response1.status_code == 201

        # Druhé přidání stejné šarže by mělo selhat
        response2 = client.post(f"/api/add_group_to_in_operation/{operation.id}/", data)
        assert response2.status_code == 400
        assert "Šarže BATCH123 už byla do této příjemky přidána." in response2.data["error"]