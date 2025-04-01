import pytest

from operation.services.operation_service import *


@pytest.mark.django_db
class TestOperationService:
    def test_create_out_operation(self, user):
        operation = create_out_operation(user=user, description="Test výdejky")

        assert operation.type == 'OUT'
        assert operation.status == 'CREATED'
        assert operation.description == "Test výdejky"

    def test_add_group_to_out_operation(self, user, batch_factory, box_factory):
        operation = create_out_operation(user=user, description="Test výdejky")
        batch = batch_factory(quantity=100)
        box = box_factory()

        group = add_group_to_out_operation(operation, batch_id=batch.id, box_id=box.id, quantity=50)

        assert group.batch.id == batch.id
        assert group.box.id == box.id
        assert group.quantity == 50
        assert group in operation.groups.all()

    def test_reserve_batches_for_out_operation_with_notification(self, user, batch_factory, group_factory):
        operation = create_out_operation(user=user, description="Test výdejky")
        batch = batch_factory(quantity=100)
        group = group_factory(batch=batch, quantity=50)
        operation.groups.add(group)

        result = reserve_batches_for_out_operation_with_notification(operation)

        assert "message" in result
        assert batch.quantity == 50  # Kontrola, že 50 ks bylo odečteno

    def test_process_out_operation(self, user, batch_factory, group_factory):
        operation = create_out_operation(user=user, description="Test výdejky")
        batch = batch_factory(quantity=100)
        group = group_factory(batch=batch, quantity=50)
        operation.groups.add(group)

        reserve_batches_for_out_operation_with_notification(operation)
        result = process_out_operation(operation)

        assert "message" in result
        assert batch.quantity == 50
        assert operation.status == 'COMPLETED'