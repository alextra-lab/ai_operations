from unittest.mock import patch

from app.orchestrator.fallback_strategy import FallbackStrategy
from app.schemas.intent import RequestType
from app.schemas.llm import ModelType


class DummyError(Exception):
    pass


def test_get_fallback_model_bad_request():
    fs = FallbackStrategy()

    class DummyBadRequest(Exception):
        pass

    err = DummyBadRequest("bad input")
    with (
        patch("app.orchestrator.fallback_strategy.BadRequestError", DummyBadRequest),
        patch("app.orchestrator.fallback_strategy.logger") as mock_logger,
    ):
        result = fs.get_fallback_model(ModelType.QUERY, err)
        assert result is None
        assert mock_logger.warning.called


def test_get_fallback_model_no_mapping():
    fs = FallbackStrategy()
    with patch("app.orchestrator.fallback_strategy.logger") as mock_logger:
        result = fs.get_fallback_model("notamodel", DummyError())
        assert result is None
        assert mock_logger.warning.called


def test_get_fallback_model_loop():
    fs = FallbackStrategy()
    # Force fallback to self
    fs.MODEL_FALLBACK_MAPPING[ModelType.QUERY] = ModelType.QUERY
    with patch("app.orchestrator.fallback_strategy.logger") as mock_logger:
        result = fs.get_fallback_model(ModelType.QUERY, DummyError())
        assert result is None
        assert mock_logger.warning.called


def test_get_fallback_model_already_tried():
    fs = FallbackStrategy()
    fallback = fs.MODEL_FALLBACK_MAPPING[ModelType.QUERY]
    with patch("app.orchestrator.fallback_strategy.logger") as mock_logger:
        result = fs.get_fallback_model(ModelType.QUERY, DummyError(), fallback_chain=[fallback])
        assert result is None
        assert mock_logger.warning.called


def test_get_fallback_model_with_intent_type():
    fs = FallbackStrategy()
    fallback = fs.MODEL_FALLBACK_MAPPING[ModelType.QUERY]
    with patch("app.orchestrator.fallback_strategy.logger") as mock_logger:
        result = fs.get_fallback_model(ModelType.QUERY, DummyError(), intent_type=RequestType.QUERY)
        assert result == fallback
        assert mock_logger.info.called


def test_get_fallback_model_without_intent_type():
    fs = FallbackStrategy()
    fallback = fs.MODEL_FALLBACK_MAPPING[ModelType.QUERY]
    with patch("app.orchestrator.fallback_strategy.logger") as mock_logger:
        result = fs.get_fallback_model(ModelType.QUERY, DummyError())
        assert result == fallback
        assert mock_logger.info.called


def test_should_attempt_fallback_max_retries():
    fs = FallbackStrategy(max_retries=2)
    with patch("app.orchestrator.fallback_strategy.logger") as mock_logger:
        result = fs.should_attempt_fallback(3, DummyError())
        assert result is False
        assert mock_logger.warning.called


def test_should_attempt_fallback_bad_request():
    fs = FallbackStrategy()

    class DummyBadRequest(Exception):
        pass

    err = DummyBadRequest("bad input")
    with (
        patch("app.orchestrator.fallback_strategy.BadRequestError", DummyBadRequest),
        patch("app.orchestrator.fallback_strategy.logger") as mock_logger,
    ):
        result = fs.should_attempt_fallback(1, err)
        assert result is False
        assert mock_logger.warning.called


def test_should_attempt_fallback_normal():
    fs = FallbackStrategy()
    result = fs.should_attempt_fallback(1, DummyError())
    assert result is True
