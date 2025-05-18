import pytest
from unittest.mock import MagicMock, patch

from chatbot.assistantDataCreator import AssistantDataCreator, get_function
from history.models import History


@pytest.mark.django_db
class TestAssistantDataCreator:

    # Nastaví základní objekty před každým testem
    def setup_method(self):
        self.creator = AssistantDataCreator()
        self.mock_user = MagicMock(id=1)
        self.mock_model = MagicMock()
        self.mock_serializer = MagicMock()

    # Ověřuje, že platný název funkce vrací callable, model a serializer
    def test_get_function_valid(self):
        func, model, serializer = get_function("getProducts")
        assert callable(func)
        assert model
        assert serializer

    # Ověřuje, že neplatný název funkce vyvolá KeyError
    def test_get_function_invalid(self):
        with pytest.raises(KeyError):
            get_function("nonexistentFunction")

    # Testuje úspěšné vytvoření objektu (serializer validní, volání save)
    def test_create_data_success(self):
        serializer_instance = MagicMock()
        serializer_instance.is_valid.return_value = True
        serializer_instance.save.return_value = MagicMock()
        self.mock_serializer.return_value = serializer_instance

        result = self.creator.create_data(
            "call1", {"name": "Item"}, 1, self.mock_model, self.mock_serializer, self.mock_user
        )
        assert "created" in result["output"]

    # Testuje selhání validace při vytváření dat (chybný vstup)
    def test_create_data_validation_error(self):
        serializer_instance = MagicMock()
        serializer_instance.is_valid.return_value = False
        serializer_instance.errors = {"error": "Invalid"}
        self.mock_serializer.return_value = serializer_instance

        result = self.creator.create_data(
            "call2", {}, 1, self.mock_model, self.mock_serializer, self.mock_user
        )
        assert "Invalid" in result["output"]

    # Testuje úspěšnou aktualizaci objektu
    def test_update_data_success(self):
        instance = MagicMock()
        self.mock_model.objects.get.return_value = instance
        self.mock_model.__name__ = "Product"

        serializer_instance = MagicMock()
        serializer_instance.is_valid.return_value = True
        serializer_instance.save.return_value = None
        self.mock_serializer.return_value = serializer_instance

        result = self.creator.update_data(
            "call3", {"id": 1}, 1, self.mock_model, self.mock_serializer, self.mock_user
        )
        assert "Product updated" in result["output"]

    # Testuje, že pokud chybí ID, vrátí se chybová hláška
    def test_update_data_missing_id(self):
        result = self.creator.update_data(
            "call4", {}, 1, self.mock_model, self.mock_serializer, self.mock_user
        )
        assert "ID is required" in result["output"]

    # Testuje, že pokud objekt není nalezen, vrátí se chybová hláška
    def test_update_data_not_found(self):
        call_id = "call5"
        product_id = 1234
        client_id = 1
        model_name = "Product"

        self.mock_model.__name__ = model_name

        # Simulace výjimky DoesNotExist
        DoesNotExist = type("DoesNotExist", (Exception,), {})
        self.mock_model.DoesNotExist = DoesNotExist
        self.mock_model.objects.get.side_effect = DoesNotExist()

        result = self.creator.update_data(
            call_id, {"id": product_id}, client_id, self.mock_model, self.mock_serializer, self.mock_user
        )

        assert result["output"] == f"{model_name} with ID {product_id} not found"

    # Testuje, že při nevalidním serializeru během aktualizace se vrátí chyba
    def test_update_data_invalid_serializer(self):
        instance = MagicMock()
        self.mock_model.objects.get.return_value = instance

        serializer_instance = MagicMock()
        serializer_instance.is_valid.return_value = False
        serializer_instance.errors = {"field": "error"}
        self.mock_serializer.return_value = serializer_instance

        result = self.creator.update_data(
            "call6", {"id": 1}, 1, self.mock_model, self.mock_serializer, self.mock_user
        )
        assert "error" in result["output"]

    # Testuje hromadné vytvoření objektů – validní data, úspěch
    def test_bulk_create_data_success(self):
        self.mock_serializer.return_value = MagicMock(
            is_valid=MagicMock(return_value=True),
            validated_data=[{"name": "A"}, {"name": "B"}]
        )
        self.mock_model.__name__ = "MockModel"

        result = self.creator.bulk_create_data(
            "call7", {"items": [{"name": "X"}, {"name": "Y"}]}, 1,
            self.mock_model, self.mock_serializer, self.mock_user
        )
        assert "2 MockModel objects created" in result["output"]

    # Testuje, že pokud `items` není seznam, vrátí se chyba
    def test_bulk_create_data_invalid_items(self):
        result = self.creator.bulk_create_data(
            "call8", {"items": "notalist"}, 1, self.mock_model, self.mock_serializer, self.mock_user
        )
        assert "must be a list" in result["output"]

    # Testuje získání seznamu stavů operací – výstup by měl být list
    def test_get_operation_statuses(self):
        result = self.creator.get_operation_statuses("call9", {}, 1, self.mock_model, self.mock_serializer, self.mock_user)
        assert result["tool_call_id"] == "call9"
        assert isinstance(result["output"], list)

    # Testuje zjednodušené získání dat – pouze počet objektů
    def test_get_data_only_count(self):
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 42
        self.mock_model.objects.all.return_value = mock_queryset

        result = self.creator.get_data(
            "call10", {"onlyCount": True}, 1, self.mock_model, self.mock_serializer, self.mock_user
        )
        assert result["output"] == "42"

    # Testuje formátování dat z modelu pomocí serializeru
    @patch("chatbot.assistantDataCreator")
    def test_format_data(self, mock_json_response):
        mock_data = [{"a": 1}]
        serializer = MagicMock()
        serializer.return_value.data = mock_data
        mock_json_response.return_value.content = b'[{"a":1}]'

        result = self.creator.format_data(serializer, mock_data, "call11")
        assert "output" in result

    # Testuje získání konkrétních historických dat
    def test_get_specific_history_data(self):
        with patch.object(self.creator, "get_history_data") as mock_get:
            mock_get.return_value = {"tool_call_id": "x", "output": "ok"}
            result = self.creator.get_specific_history_data("x", {}, 1, History, MagicMock(), self.mock_user, "operation")
            assert result["output"] == "ok"

    # Testuje filtrování historických dat podle časového rozmezí a typu
    def test_get_history_data_filters(self):
        mock_qs = MagicMock()
        self.mock_model.objects.all.return_value = mock_qs
        mock_filtered = MagicMock()
        mock_qs.filter.return_value = mock_filtered

        with patch.object(self.creator, "format_data") as mock_format:
            mock_format.return_value = {"tool_call_id": "call12", "output": "filtered"}
            result = self.creator.get_history_data("call12", {
                "type": "operation",
                "from_timestamp": "2024-01-01",
                "to_timestamp": "2024-12-31"
            }, 1, self.mock_model, self.mock_serializer, self.mock_user)
            assert result["output"] == "filtered"