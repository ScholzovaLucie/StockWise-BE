import pytest
from user.models import User


# Test registrace s validními údaji
@pytest.mark.django_db
def test_register_user(authenticated_client):
    response = authenticated_client.post("/api/auth/register/", {
        "email": "test@example.com",
        "password": "StrongPass1!"
    })
    assert response.status_code == 201
    assert "user" in response.data


# Test registrace se slabým heslem
@pytest.mark.django_db
def test_register_user_weak_password(authenticated_client):
    response = authenticated_client.post("/api/auth/register/", {
        "email": "test@example.com",
        "password": "weak"
    })
    assert response.status_code == 400
    assert "error" in response.data


# Test přihlášení s platnými údaji
@pytest.mark.django_db
def test_login_user(api_client, user_factory):
    password = "StrongPass1!"
    user = user_factory(password=password)
    response = api_client.post("/api/auth/login/", {
        "email": user.email,
        "password": password
    })
    assert response.status_code == 200
    assert "user" in response.json()


# Získání dat o aktuálně přihlášeném uživateli
@pytest.mark.django_db
def test_get_authenticated_user(authenticated_client, user_factory):
    user = User.objects.first()
    response = authenticated_client.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.data["email"] == user.email


# Test změny hesla (předpokládá platné staré heslo 'testpass')
@pytest.mark.django_db
def test_change_password(authenticated_client, user_factory):
    response = authenticated_client.post("/api/auth/change-password/", {
        "old_password": 'testpass',
        "new_password": "NewPass1!",
        "confirm_password": "NewPass1!"
    })
    assert response.status_code == 200


# Test odeslání požadavku na reset hesla
@pytest.mark.django_db
def test_request_password_reset(authenticated_client):
    response = authenticated_client.post("/api/auth/request-password-reset/", {
        "email": "testuser@example.com"
    })
    assert response.status_code == 200


# Test odhlášení uživatele
@pytest.mark.django_db
def test_logout_user(authenticated_client):
    response = authenticated_client.post("/api/auth/logout/")
    assert response.status_code == 200