from unittest.mock import patch

from app.orchestrator.parameter_manager import ParameterManager


class FakeIntent:
    value = "not_a_real_model"


def test_get_intent_temperature_invalid():
    pm = ParameterManager()
    with patch("app.orchestrator.parameter_manager.logger") as mock_logger:
        temp = pm.get_intent_temperature(FakeIntent)
        assert temp == 0.7
        assert mock_logger.warning.called


def test_get_intent_max_tokens_invalid():
    pm = ParameterManager()
    with patch("app.orchestrator.parameter_manager.logger") as mock_logger:
        tokens = pm.get_intent_max_tokens(FakeIntent)
        assert tokens == 2048
        assert mock_logger.warning.called


def test_get_intent_parameters_invalid():
    pm = ParameterManager()
    with patch("app.orchestrator.parameter_manager.logger") as mock_logger:
        params = pm.get_intent_parameters(FakeIntent)
        assert params["temperature"] == 0.7
        assert params["max_tokens"] == 2048
        assert mock_logger.warning.called
