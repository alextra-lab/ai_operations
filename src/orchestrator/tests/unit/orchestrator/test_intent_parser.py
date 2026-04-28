from unittest.mock import patch

import pytest
from app.orchestrator.intent_parser import IntentParser
from app.schemas.intent import IntentRequest, RequestType


@pytest.fixture
def sample_request():
    return IntentRequest(
        query="Summarize the latest threat.", request_type=RequestType.SUMMARIZATION
    )


def test_intent_parser_init_logs(monkeypatch):
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    with patch("app.orchestrator.intent_parser.logger") as mock_logger:
        parser = IntentParser(config={"foo": "bar"})
        assert parser.config == {"foo": "bar"}
        assert parser.logger == mock_logger
        assert mock_logger.info.call_count >= 2
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)


def test_parse_intent_basic(sample_request):
    parser = IntentParser()
    response = parser.parse_intent(sample_request)
    assert response.detected_type == RequestType.SUMMARIZATION
    assert response.explicit_type == RequestType.SUMMARIZATION
    assert response.inferred_type is None
    assert response.confidence == 1.0
    assert response.query == sample_request.query
    assert response.metadata["detection_method"] == "deterministic"
    assert "processing_time" in response.metadata


def test_parse_intent_with_config_metadata(sample_request):
    parser = IntentParser(config={"include_config_in_metadata": True, "foo": 123})
    response = parser.parse_intent(sample_request)
    assert "config" in response.metadata
    assert response.metadata["config"]["foo"] == 123


@pytest.mark.parametrize(
    ("query", "expected_type"),
    [
        ("Write a YARA rule for this IOC", RequestType.RULE_GENERATION),
        ("Can you summarize this report?", RequestType.SUMMARIZATION),
        ("Add more information to this IOC", RequestType.ENRICHMENT),
        ("What is the latest threat?", RequestType.QUERY),
    ],
)
def test_keyword_based_classification(query, expected_type):
    parser = IntentParser()
    detected_type, confidence = parser._keyword_based_classification(query)
    assert detected_type == expected_type
    assert 0.5 < confidence <= 0.8 or detected_type == RequestType.QUERY


def test_analyze_query_text_not_implemented():
    parser = IntentParser()
    with pytest.raises(NotImplementedError):
        parser.analyze_query_text("What is the latest threat?")


def test_calculate_confidence_score_not_implemented():
    parser = IntentParser()
    with pytest.raises(NotImplementedError):
        parser.calculate_confidence_score("query", RequestType.QUERY)


def test_compare_intent_types_not_implemented():
    parser = IntentParser()
    with pytest.raises(NotImplementedError):
        parser.compare_intent_types(RequestType.QUERY, RequestType.SUMMARIZATION)


def test_enhanced_intent_detection_match():
    parser = IntentParser()
    req = IntentRequest(query="Summarize this", request_type=RequestType.SUMMARIZATION)
    resp = parser.enhanced_intent_detection(req)
    assert resp.detected_type == RequestType.SUMMARIZATION
    assert resp.inferred_type == RequestType.SUMMARIZATION
    assert resp.confidence == 0.95
    assert resp.metadata["detection_method"] == "hybrid"


def test_enhanced_intent_detection_mismatch():
    parser = IntentParser()
    req = IntentRequest(query="Write a YARA rule", request_type=RequestType.QUERY)
    resp = parser.enhanced_intent_detection(req)
    assert resp.detected_type == RequestType.QUERY
    assert resp.inferred_type == RequestType.RULE_GENERATION
    assert resp.confidence == 0.7
    assert resp.metadata["detection_method"] == "hybrid"
