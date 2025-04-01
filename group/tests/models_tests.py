from unittest import TestCase

import pytest
from product.models import Product
from batch.models import Batch
from group.models import Group


class GroupTest:

    @pytest.mark.django_db
    def test_product_amount_updates(self):
        product = Product.objects.create(name="Test Produkt", sku="TEST123", client_id=1)

        # Neexistují žádné Group, amount by mělo být 0
        assert product.amount == 0

        batch = Batch.objects.create(product=product, batch_number="BATCH001")
        Group.objects.create(batch=batch, quantity=10)

        # Po přidání Group by mělo být množství 10
        product.refresh_from_db()
        assert product.amount == 10

        # Při výdeji množství klesne na 0
        Group.objects.filter(batch=batch).delete()
        product.refresh_from_db()
        assert product.amount == 0