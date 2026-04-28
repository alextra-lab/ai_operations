"""Unit tests for model selection (ADR-069)."""

import pytest
from app.orchestrator.model_selection import ModelSelector, load_intent_defaults_from_async_db
from app.schemas.intent import RequestType


@pytest.fixture
def preloaded_defaults():
    """Preloaded intent defaults for tests (keys match RequestType.value)."""
    return {
        "QUERY": "model-query-001",
        "RULE_GENERATION": "model-rule-001",
        "SUMMARIZATION": "model-summary-001",
        "ENRICHMENT": "model-enrich-001",
    }


@pytest.fixture
def selector(preloaded_defaults):
    """ModelSelector with preloaded defaults."""
    return ModelSelector(preloaded_defaults=preloaded_defaults)


def test_get_model_for_intent_returns_model_id_when_configured(selector, preloaded_defaults):
    """get_model_for_intent returns model_id for configured intents."""
    for intent in RequestType:
        if intent.value in preloaded_defaults:
            assert selector.get_model_for_intent(intent) == preloaded_defaults[intent.value]


def test_get_model_for_intent_raises_when_unconfigured():
    """get_model_for_intent raises ValueError when intent has no default."""
    selector = ModelSelector(preloaded_defaults={"QUERY": "model-query-001"})
    with pytest.raises(ValueError, match="No default model configured for intent SUMMARIZATION"):
        selector.get_model_for_intent(RequestType.SUMMARIZATION)


def test_get_default_model_returns_model_id_when_configured(selector, preloaded_defaults):
    """get_default_model returns model_id for configured intents."""
    assert (
        selector.get_default_model(RequestType.QUERY) == preloaded_defaults[RequestType.QUERY.value]
    )


def test_get_default_model_returns_none_when_unconfigured():
    """get_default_model returns None when intent has no default."""
    selector = ModelSelector(preloaded_defaults={"QUERY": "model-query-001"})
    assert selector.get_default_model(RequestType.SUMMARIZATION) is None


def test_get_all_defaults_returns_copy(selector, preloaded_defaults):
    """get_all_defaults returns a copy of the configured defaults."""
    defaults = selector.get_all_defaults()
    assert defaults == preloaded_defaults
    assert defaults is not selector._intent_defaults_cache


def test_selector_without_db_or_preloaded_raises_for_any_intent():
    """ModelSelector without db or preloaded_defaults raises for any intent."""
    selector = ModelSelector()
    with pytest.raises(ValueError, match="No default model configured"):
        selector.get_model_for_intent(RequestType.QUERY)


def test_selector_with_empty_preloaded_raises():
    """ModelSelector with empty preloaded_defaults raises for any intent."""
    selector = ModelSelector(preloaded_defaults={})
    with pytest.raises(ValueError, match="No default model configured"):
        selector.get_model_for_intent(RequestType.QUERY)


@pytest.mark.asyncio
async def test_load_intent_defaults_from_async_db_returns_mapping():
    """load_intent_defaults_from_async_db returns (model_defaults, temperature_defaults)."""
    from unittest.mock import AsyncMock

    mock_rows = [
        ("QUERY", "model-query-001", 0.7),
        ("SUMMARIZATION", "model-sum-001", None),
    ]
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_rows)

    model_defaults, temperature_defaults = await load_intent_defaults_from_async_db(mock_session)
    assert model_defaults == {"QUERY": "model-query-001", "SUMMARIZATION": "model-sum-001"}
    assert temperature_defaults == {"QUERY": 0.7}
