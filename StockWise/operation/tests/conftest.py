import os
import django
from pytest_django.lazy_django import skip_if_no_django

import pytest
from django.contrib.auth import get_user_model
from batch.models import Batch
from box.models import Box
from client.models import Client
from group.models import Group
from operation.models import Operation
from product.models import Product
from user.models import User

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StockWise.settings')

skip_if_no_django()
django.setup()


@pytest.fixture
def user():
    """
    Fixture pro vytvoření základního uživatele.
    """
    return User.objects.create(email="testuser", password="testpass")

@pytest.fixture
def client():
    """
    Fixture pro vytvoření základního uživatele.
    """
    return Client.objects.create(
            name="testclient",
            email="testclient",
        )


@pytest.fixture
def batch_factory(client):
    """
    Fixture pro dynamické vytváření šarží.
    """
    def create_batch(amount, expiration_date):
        product = Product.objects.create(
            client=client,
            sku="testsku",
            name="testname",
            description='test',
        )
        product.set_test_amount(amount)

        return Batch.objects.create(
            expiration_date=expiration_date,
            product=product,
        )
    return create_batch


@pytest.fixture
def box_factory():
    """
    Fixture pro dynamické vytváření krabic.
    """
    def create_box(label="Box 1", status="active"):
        return Box.objects.create(
            label=label,
            status=status
        )
    return create_box


@pytest.fixture
def operation_factory():
    """
    Fixture pro dynamické vytváření operací.
    """
    def create_operation(user, type="OUT", status="CREATED", description=None):
        return Operation.objects.create(
            user=user,
            type=type,
            status=status,
            description=description
        )
    return create_operation


@pytest.fixture
def group_factory():
    """
    Fixture pro dynamické vytváření skupin.
    """
    def create_group(batch, box=None, quantity=50):
        return Group.objects.create(
            batch=batch,
            box=box,
            quantity=quantity
        )
    return create_group