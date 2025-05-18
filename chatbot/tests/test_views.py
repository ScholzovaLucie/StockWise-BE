import pytest
from django.urls import reverse
from unittest.mock import patch


@pytest.mark.django_db
class TestStatisticsView:
    # Testuje chybějící parametry v požadavku – musí vrátit 400 a chybovou hlášku
    def test_missing_params(self, authenticated_client):
        response = authenticated_client.post(reverse("chatbot_statistics"))
        assert response.status_code == 400
        assert "error" in response.json()

    # Testuje zadání neexistujícího klienta – očekává se 404
    def test_invalid_client(self, authenticated_client):
        response = authenticated_client.post(reverse("chatbot_statistics"), {
            "client": 999,
            "stat_id": "stockSummary"
        })
        assert response.status_code == 404
        assert "error" in response.json()

    # Testuje zadání neexistujícího identifikátoru statistiky – očekává se 400
    def test_invalid_stat_id(self, authenticated_client, user_with_client):
        client_id = user_with_client.client.first().id
        response = authenticated_client.post(reverse("chatbot_statistics"), {
            "client": client_id,
            "stat_id": "invalidStat"
        })
        assert response.status_code == 400
        assert "error" in response.json()

    # Testuje správný požadavek na statistiku – mockuje odpověď OpenAIHandleru
    @patch("chatbot.views.OpenAIHandler.run_prompt")
    def test_valid_stat_id(self, mock_run_prompt, authenticated_client, user_with_client):
        mock_run_prompt.return_value = {
            "element": "div",
            "content": "Mocked statistic response",
            "class": "assistant"
        }
        client_id = user_with_client.client.first().id
        response = authenticated_client.post(reverse("chatbot_statistics"), {
            "client": client_id,
            "stat_id": "stockSummary"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Mocked statistic response"
        assert data["element"] == "div"


@pytest.mark.django_db
class TestChatbotView:
    # Testuje chybějící parametr `client` – očekává se 400 a chyba
    def test_missing_client(self, authenticated_client):
        response = authenticated_client.post(reverse("chatbot"), {
            "prompt": "Ahoj"
        })
        assert response.status_code == 400
        assert "error" in response.json()

    # Testuje chybějící parametr `prompt` – očekává se 400 a chyba
    def test_missing_prompt(self, authenticated_client, user_with_client):
        client_id = user_with_client.client.first().id
        response = authenticated_client.post(reverse("chatbot"), {
            "client": client_id
        })
        assert response.status_code == 400
        assert "error" in response.json()

    # Testuje správný požadavek na chatbot – mockuje odpověď OpenAIHandleru
    @patch("chatbot.views.OpenAIHandler.run_prompt")
    def test_valid_prompt(self, mock_run_prompt, authenticated_client, user_with_client):
        mock_run_prompt.return_value = {
            "element": "div",
            "content": "Mocked chatbot response",
            "class": "assistant"
        }
        client_id = user_with_client.client.first().id
        response = authenticated_client.post(reverse("chatbot"), {
            "client": client_id,
            "prompt": "Jaký je stav skladu?"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Mocked chatbot response"
        assert data["element"] == "div"