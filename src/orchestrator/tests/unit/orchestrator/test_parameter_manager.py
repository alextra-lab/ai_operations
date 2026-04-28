from app.orchestrator.parameter_manager import ParameterManager
from app.schemas.intent import RequestType
from app.schemas.llm import ModelType


def test_get_model_temperature_and_max_tokens_defaults():
    pm = ParameterManager()
    for model_type in ModelType:
        temp = pm.get_model_temperature(model_type)
        tokens = pm.get_model_max_tokens(model_type)
        assert isinstance(temp, float)
        assert isinstance(tokens, int)
        # Should match metadata defaults if no env override
        assert temp == model_type.metadata["default_temperature"]
        assert tokens == model_type.metadata["max_tokens"]


def test_get_model_parameters():
    pm = ParameterManager()
    for model_type in ModelType:
        params = pm.get_model_parameters(model_type)
        assert "temperature" in params
        assert "max_tokens" in params
        assert params["temperature"] == pm.get_model_temperature(model_type)
        assert params["max_tokens"] == pm.get_model_max_tokens(model_type)


def test_get_intent_temperature_and_max_tokens_defaults():
    pm = ParameterManager()
    for intent_type in RequestType:
        temp = pm.get_intent_temperature(intent_type)
        tokens = pm.get_intent_max_tokens(intent_type)
        assert isinstance(temp, float)
        assert isinstance(tokens, int)


def test_get_intent_parameters():
    pm = ParameterManager()
    for intent_type in RequestType:
        params = pm.get_intent_parameters(intent_type)
        assert "temperature" in params
        assert "max_tokens" in params


def test_get_intent_temperature_invalid():
    pm = ParameterManager()

    class FakeIntent:
        value = "not_a_real_model"

    # Should fallback to default
    assert pm.get_intent_temperature(FakeIntent) == 0.7


def test_get_intent_max_tokens_invalid():
    pm = ParameterManager()

    class FakeIntent:
        value = "not_a_real_model"

    # Should fallback to default
    assert pm.get_intent_max_tokens(FakeIntent) == 2048


def test_get_intent_parameters_invalid():
    pm = ParameterManager()

    class FakeIntent:
        value = "not_a_real_model"

    params = pm.get_intent_parameters(FakeIntent)
    assert params["temperature"] == 0.7
    assert params["max_tokens"] == 2048
