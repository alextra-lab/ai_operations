"""
Integration tests for B2-F2: Enhanced Metrics in Response

This module tests the comprehensive metrics implementation across the entire
orchestration pipeline, ensuring that metrics are properly collected,
consolidated, and included in API responses.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.orchestrator.app.main import create_app
from src.orchestrator.app.schemas.response import (
    ConsolidatedMetrics,
    FormattedResponse,
    GuardMetrics,
    ModelMetrics,
    RetrievalMetrics,
)


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_auth_token():
    """Mock authentication token."""
    return "mock-jwt-token"


@pytest.fixture
def sample_metrics():
    """Sample metrics data for testing."""
    return {
        "retrieval": RetrievalMetrics(
            top_k=10,
            hits=5,
            avg_similarity=0.85,
            min_similarity=0.72,
            max_similarity=0.95,
            source_count=3,
        ),
        "guard": GuardMetrics(
            risk_score=0.15, modified=False, details={"prompt_injection": False, "toxicity": 0.1}
        ),
        "model": ModelMetrics(
            model_id="QUERY",
            tokens_in=150,
            tokens_out=300,
            total_tokens=450,
            processing_time=2.5,
            metadata={"temperature": 0.7},
        ),
        "confidence_score": 0.87,
        "calculation_method": "weighted_consolidation",
    }


class TestEnhancedMetrics:
    """Test enhanced metrics implementation."""

    def test_retrieval_metrics_schema(self, sample_metrics):
        """Test RetrievalMetrics schema validation."""
        retrieval = sample_metrics["retrieval"]

        assert retrieval.top_k == 10
        assert retrieval.hits == 5
        assert retrieval.avg_similarity == 0.85
        assert retrieval.min_similarity == 0.72
        assert retrieval.max_similarity == 0.95
        assert retrieval.source_count == 3

        # Test validation
        assert 0 <= retrieval.avg_similarity <= 1
        assert 0 <= retrieval.min_similarity <= 1
        assert 0 <= retrieval.max_similarity <= 1
        assert retrieval.top_k >= 0
        assert retrieval.hits >= 0
        assert retrieval.source_count >= 0

    def test_guard_metrics_schema(self, sample_metrics):
        """Test GuardMetrics schema validation."""
        guard = sample_metrics["guard"]

        assert guard.risk_score == 0.15
        assert guard.modified is False
        assert "prompt_injection" in guard.details
        assert "toxicity" in guard.details

        # Test validation
        assert 0 <= guard.risk_score <= 1
        assert isinstance(guard.modified, bool)
        assert isinstance(guard.details, dict)

    def test_model_metrics_schema(self, sample_metrics):
        """Test ModelMetrics schema validation."""
        model = sample_metrics["model"]

        assert model.model_id == "QUERY"
        assert model.tokens_in == 150
        assert model.tokens_out == 300
        assert model.total_tokens == 450
        assert model.processing_time == 2.5
        assert "temperature" in model.metadata

        # Test validation
        assert model.tokens_in >= 0
        assert model.tokens_out >= 0
        assert model.total_tokens >= 0
        assert model.processing_time >= 0
        assert isinstance(model.metadata, dict)

    def test_consolidated_metrics_schema(self, sample_metrics):
        """Test ConsolidatedMetrics schema validation."""
        consolidated = ConsolidatedMetrics(
            retrieval=sample_metrics["retrieval"],
            guard=sample_metrics["guard"],
            model=sample_metrics["model"],
            confidence_score=sample_metrics["confidence_score"],
            calculation_method=sample_metrics["calculation_method"],
        )

        assert consolidated.retrieval is not None
        assert consolidated.guard is not None
        assert consolidated.model is not None
        assert consolidated.confidence_score == 0.87
        assert consolidated.calculation_method == "weighted_consolidation"

        # Test validation
        assert 0 <= consolidated.confidence_score <= 1

    def test_formatted_response_with_metrics(self, sample_metrics):
        """Test FormattedResponse includes comprehensive metrics."""
        consolidated = ConsolidatedMetrics(
            retrieval=sample_metrics["retrieval"],
            guard=sample_metrics["guard"],
            model=sample_metrics["model"],
            confidence_score=sample_metrics["confidence_score"],
            calculation_method=sample_metrics["calculation_method"],
        )

        response = FormattedResponse(
            response="Test response with comprehensive metrics",
            sources=[],
            confidence=0.87,
            metrics=consolidated,
            suggested_actions=None,
            request_id="test-request-123",
        )

        assert response.metrics is not None
        assert response.metrics.retrieval is not None
        assert response.metrics.guard is not None
        assert response.metrics.model is not None
        assert response.metrics.confidence_score == 0.87

    def test_confidence_calculation_weighted_formula(self):
        """Test that confidence calculation follows the weighted formula."""
        from src.orchestrator.app.orchestrator.response_formatter import ResponseFormatter

        formatter = ResponseFormatter()

        # Test with high-quality metrics
        retrieval = RetrievalMetrics(
            top_k=10,
            hits=8,
            avg_similarity=0.9,
            min_similarity=0.8,
            max_similarity=0.95,
            source_count=5,
        )

        guard = GuardMetrics(risk_score=0.05, modified=False, details={})

        model = ModelMetrics(
            model_id="QUERY",
            tokens_in=100,
            tokens_out=200,
            total_tokens=300,
            processing_time=1.5,
            metadata={},
        )

        confidence = formatter._calculate_consolidated_confidence(retrieval, guard, model, [])

        # Should be reasonably high confidence due to good metrics
        assert confidence > 0.7
        assert 0 <= confidence <= 1

        # Test with low-quality metrics
        retrieval_low = RetrievalMetrics(
            top_k=10,
            hits=2,
            avg_similarity=0.3,
            min_similarity=0.2,
            max_similarity=0.4,
            source_count=1,
        )

        guard_high_risk = GuardMetrics(risk_score=0.8, modified=True, details={})

        confidence_low = formatter._calculate_consolidated_confidence(
            retrieval_low, guard_high_risk, model, []
        )

        # Should be lower confidence due to poor metrics
        assert confidence_low < confidence
        assert 0 <= confidence_low <= 1

    def test_metrics_consolidation_with_missing_data(self):
        """Test metrics consolidation when some data is missing."""
        from src.orchestrator.app.orchestrator.response_formatter import ResponseFormatter
        from src.orchestrator.app.schemas.llm import LLMResponse, ModelType

        formatter = ResponseFormatter()

        llm_response = LLMResponse(
            response="Test response",
            model_used=ModelType.QUERY,
            tokens_used=300,
            processing_time=2.0,
            metadata={},
        )

        # Test with no retrieval metrics (RAG disabled)
        consolidated_no_retrieval = formatter._consolidate_metrics(llm_response, [], None, None)

        assert consolidated_no_retrieval.retrieval is None
        assert consolidated_no_retrieval.guard is None
        assert consolidated_no_retrieval.model is not None
        assert 0 <= consolidated_no_retrieval.confidence_score <= 1

        # Test with partial metrics
        guard_metrics = {"risk_score": 0.2, "modified": False, "details": {}}

        consolidated_partial = formatter._consolidate_metrics(llm_response, [], None, guard_metrics)

        assert consolidated_partial.retrieval is None
        assert consolidated_partial.guard is not None
        assert consolidated_partial.model is not None

    @patch(
        "src.orchestrator.app.orchestrator.response_formatter.ResponseFormatter._consolidate_metrics"
    )
    def test_response_formatter_includes_metrics(self, mock_consolidate):
        """Test that ResponseFormatter includes metrics in the response."""
        from src.orchestrator.app.orchestrator.response_formatter import ResponseFormatter
        from src.orchestrator.app.schemas.llm import LLMResponse, ModelType

        # Mock consolidated metrics
        mock_consolidated = ConsolidatedMetrics(
            retrieval=None,  # type: ignore[arg-type]
            guard=None,  # type: ignore[arg-type]
            model=ModelMetrics(
                model_id="QUERY",
                tokens_in=100,
                tokens_out=200,
                total_tokens=300,
                processing_time=1.5,
                metadata={},
            ),
            confidence_score=0.75,
            calculation_method="weighted_consolidation",
        )
        mock_consolidate.return_value = mock_consolidated

        formatter = ResponseFormatter()

        llm_response = LLMResponse(
            response="Test response",
            model_used=ModelType.QUERY,
            tokens_used=300,
            processing_time=1.5,
            metadata={},
        )

        formatted_response = formatter.process(
            llm_response, request_id="test-123", retrieval_metrics=None, guard_metrics=None
        )

        assert formatted_response.metrics is not None
        assert formatted_response.metrics.confidence_score == 0.75
        assert formatted_response.metrics.model is not None

    def test_metrics_json_serialization(self, sample_metrics):
        """Test that metrics can be properly serialized to JSON."""
        consolidated = ConsolidatedMetrics(
            retrieval=sample_metrics["retrieval"],
            guard=sample_metrics["guard"],
            model=sample_metrics["model"],
            confidence_score=sample_metrics["confidence_score"],
            calculation_method=sample_metrics["calculation_method"],
        )

        response = FormattedResponse(
            response="Test response",
            sources=[],
            confidence=0.87,
            metrics=consolidated,
            suggested_actions=None,
            request_id="test-request-123",
        )

        # Test JSON serialization
        json_data = response.model_dump()

        assert "metrics" in json_data
        assert json_data["metrics"]["confidence_score"] == 0.87
        assert json_data["metrics"]["retrieval"]["avg_similarity"] == 0.85
        assert json_data["metrics"]["guard"]["risk_score"] == 0.15
        assert json_data["metrics"]["model"]["model_id"] == "QUERY"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
