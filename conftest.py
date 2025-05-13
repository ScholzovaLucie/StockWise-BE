import pytest
from rest_framework.test import APIClient
from user.models import User
from client.models import Client


@pytest.fixture
def client_factory(db):
    """
    Fixture pro vytvoření nové instance Client.

    :param db: Django databázová fixture (automaticky předána)
    :return: Funkce pro vytvoření klienta s volitelnými parametry
    """
    def create_client(**kwargs) -> Client:
        defaults = {
            'name': 'Test Client',
        }
        defaults.update(kwargs)
        return Client.objects.create(**defaults)
    return create_client


@pytest.fixture
def user_factory(db, client_factory):
    """
    Fixture pro vytvoření uživatele a přiřazení výchozího klienta.

    :param db: Django databázová fixture
    :param client_factory: Fixture pro vytvoření klienta
    :return: Funkce pro vytvoření uživatele s klientem
    """
    def create_user(email="user@example.com", password="pass", **kwargs) -> User:
        user = User.objects.create_user(email=email, password=password, **kwargs)
        user.client.add(client_factory())
        return user
    return create_user


@pytest.fixture
def api_client() -> APIClient:
    """
    Fixture pro vytvoření neautentizovaného API klienta.

    :return: Instance APIClient
    """
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user_with_client):
    """
    Fixture pro vytvoření autentizovaného API klienta s výchozím uživatelem.

    :param api_client: Neautentizovaný klient
    :param user_factory: Fixture pro vytvoření uživatele
    :return: Autentizovaný APIClient
    """
    api_client.force_authenticate(user=user_with_client)
    return api_client


@pytest.fixture
@pytest.mark.django_db
def user_with_client(client_factory):
    """
    Fixture pro vytvoření uživatele a ruční přiřazení klienta (bez hesla přes create_user).

    :param client_factory: Fixture pro vytvoření klienta
    :return: Instance User s přiřazeným klientem
    """
    client = client_factory()
    user = User.objects.create_user(
        email='testuser@example.com',
        password='testpass'  # POZOR: toto nehashuje heslo, jen pro testy!
    )
    user.client.add(client)
    return user