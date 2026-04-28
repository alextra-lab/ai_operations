"""
Integration tests for P2-FIX-09 execution metrics enhancements.

Tests the complete flow of enhanced metrics including cost estimation,
timing breakdown, model parameters, and security flags.
"""

from src.orchestrator.app.orchestrator.response_formatter import ResponseFormatter
from src.orchestrator.app.schemas.llm import LLMResponse, ModelType


class TestP2Fix09MetricsIntegration:
    """Integration tests for P2-FIX-09 metrics enhancements."""

    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = ResponseFormatter()

    def test_full_metrics_with_cost_estimation(self):
        """Test complete metrics consolidation with cost estimation."""
        # Arrange
        llm_response = LLMResponse(
            response="This is a test response",
            model_used=ModelType.QUERY,
            tokens_used=1500,
            processing_time=2.5,
            metadata={
                "model_id": "gpt-4o-mini",  # Actual model ID for cost estimation
                "tokens_in": 1000,
                "tokens_out": 500,
                "temperature": 0.7,
                "max_tokens": 2000,
            },
        )

        retrieval_metrics = {
            "top_k": 5,
            "hits": 3,
            "similarity_scores": [0.95, 0.87, 0.76],
        }

        guard_metrics = {
            "risk_score": 0.2,
            "modified": False,
            "details": {
                "scanners": {
                    "anonymize": {"passed": True, "score": 0.1},  # Actual scanner name
                    "prompt_injection": {
                        "passed": True,
                        "score": 0.15,
                    },  # Actual scanner name
                }
            },
        }

        # Act
        consolidated = self.formatter._consolidate_metrics(
            llm_response=llm_response,
            sources=[],
            retrieval_metrics=retrieval_metrics,
            guard_metrics=guard_metrics,
        )

        # Assert - Cost estimation
        assert consolidated.model.metadata["cost_estimate"] is not None
        assert consolidated.model.metadata["cost_estimate"] > 0
        assert consolidated.model.metadata["cost_breakdown"] is not None
        assert "input_cost" in consolidated.model.metadata["cost_breakdown"]
        assert "output_cost" in consolidated.model.metadata["cost_breakdown"]
        assert "total_cost" in consolidated.model.metadata["cost_breakdown"]
        assert "pricing_source" in consolidated.model.metadata["cost_breakdown"]

        # Assert - Model parameters
        assert consolidated.model.metadata["parameters"] is not None
        assert consolidated.model.metadata["parameters"]["temperature"] == 0.7
        assert consolidated.model.metadata["parameters"]["max_tokens"] == 2000

        # Assert - Security flags
        assert consolidated.guard.details["pii_detected"] is False
        assert consolidated.guard.details["toxicity_detected"] is False
        assert consolidated.guard.details["jailbreak_attempt"] is False
        assert consolidated.guard.details["content_filtered"] is False

        # Assert - Retrieval metrics
        assert consolidated.retrieval.top_k == 5
        assert consolidated.retrieval.hits == 3
        assert consolidated.retrieval.avg_similarity > 0.8

    def test_metrics_with_security_alerts(self):
        """Test metrics with security flags triggered."""
        # Arrange
        llm_response = LLMResponse(
            response="Response with sensitive content",
            model_used=ModelType.QUERY,
            tokens_used=2000,
            processing_time=3.0,
            metadata={
                "model_id": "claude-3-5-sonnet-20241022",
                "tokens_in": 1500,
                "tokens_out": 500,
            },
        )

        guard_metrics = {
            "risk_score": 0.7,
            "modified": True,
            "details": {
                "scanners": {
                    "anonymize": {"passed": False, "score": 0.8},  # PII detected
                    "secrets": {"passed": False, "score": 0.6},  # Secrets detected
                    "prompt_injection": {"passed": True, "score": 0.2},  # No jailbreak
                }
            },
        }

        # Act
        consolidated = self.formatter._consolidate_metrics(
            llm_response=llm_response,
            sources=[],
            retrieval_metrics=None,
            guard_metrics=guard_metrics,
        )

        # Assert - Security flags should match scanner results
        assert consolidated.guard.details["pii_detected"] is True  # anonymize failed
        assert consolidated.guard.details["secrets_detected"] is True  # secrets failed
        assert consolidated.guard.details["jailbreak_attempt"] is False  # prompt_injection passed
        assert consolidated.guard.details["content_filtered"] is True  # Some scanners failed
        assert len(consolidated.guard.details["blocked_categories"]) >= 2  # anonymize + secrets

        # Assert - High risk score
        assert consolidated.guard.risk_score == 0.7
        assert consolidated.guard.modified is True

        # Assert - Cost estimation still works
        assert consolidated.model.metadata["cost_estimate"] is not None
        assert consolidated.model.metadata["cost_estimate"] > 0

    def test_metrics_with_timing_breakdown(self):
        """Test metrics with timing breakdown from metadata."""
        # Arrange
        llm_response = LLMResponse(
            response="Test response",
            model_used=ModelType.QUERY,
            tokens_used=500,
            processing_time=1.0,
            metadata={
                "model_id": "gpt-4o-mini",
                "tokens_in": 300,
                "tokens_out": 200,
                "timing": {
                    "retrieval_time": 0.2,
                    "guard_time": 0.1,
                    "model_time": 0.7,
                    "total_time": 1.0,
                    "breakdown": {
                        "retrieval_pct": 20.0,
                        "guard_pct": 10.0,
                        "model_pct": 70.0,
                    },
                },
            },
        )

        # Act
        consolidated = self.formatter._consolidate_metrics(
            llm_response=llm_response,
            sources=[],
            retrieval_metrics=None,
            guard_metrics=None,
        )

        # Assert - Timing breakdown
        assert consolidated.model.metadata["timing_breakdown"] is not None
        timing = consolidated.model.metadata["timing_breakdown"]
        assert timing["retrieval_time"] == 0.2
        assert timing["guard_time"] == 0.1
        assert timing["model_time"] == 0.7
        assert timing["total_time"] == 1.0
        assert timing["breakdown"]["retrieval_pct"] == 20.0
        assert timing["breakdown"]["guard_pct"] == 10.0
        assert timing["breakdown"]["model_pct"] == 70.0

    def test_metrics_with_all_enhancements(self):
        """Test metrics with all P2-FIX-09 enhancements combined."""
        # Arrange
        llm_response = LLMResponse(
            response="Comprehensive test response",
            model_used=ModelType.QUERY,
            tokens_used=1000,
            processing_time=2.0,
            metadata={
                "model_id": "gpt-4o-mini",
                "tokens_in": 600,
                "tokens_out": 400,
                "temperature": 0.8,
                "max_tokens": 1500,
                "top_p": 0.95,
                "top_k": 50,
                "timing": {
                    "retrieval_time": 0.5,
                    "guard_time": 0.3,
                    "model_time": 1.2,
                    "total_time": 2.0,
                    "breakdown": {
                        "retrieval_pct": 25.0,
                        "guard_pct": 15.0,
                        "model_pct": 60.0,
                    },
                },
            },
        )

        retrieval_metrics = {
            "top_k": 10,
            "hits": 8,
            "similarity_scores": [0.98, 0.95, 0.92, 0.89, 0.85, 0.81, 0.78, 0.75],
        }

        guard_metrics = {
            "risk_score": 0.15,
            "modified": False,
            "details": {
                "scanners": {
                    "anonymize": {"passed": True, "score": 0.1},
                    "secrets": {"passed": True, "score": 0.05},
                    "prompt_injection": {"passed": True, "score": 0.08},
                    "gibberish": {"passed": True, "score": 0.02},
                }
            },
        }

        # Act
        consolidated = self.formatter._consolidate_metrics(
            llm_response=llm_response,
            sources=[],
            retrieval_metrics=retrieval_metrics,
            guard_metrics=guard_metrics,
        )

        # Assert - All components present
        assert consolidated.retrieval is not None
        assert consolidated.guard is not None
        assert consolidated.model is not None
        assert consolidated.confidence_score > 0

        # Assert - Cost estimation
        assert "cost_estimate" in consolidated.model.metadata
        assert "cost_breakdown" in consolidated.model.metadata
        cost_breakdown = consolidated.model.metadata["cost_breakdown"]
        assert cost_breakdown["total_cost"] > 0
        assert cost_breakdown["currency"] == "USD"
        assert cost_breakdown["pricing_source"] == "hardcoded"

        # Assert - Model parameters
        assert "parameters" in consolidated.model.metadata
        params = consolidated.model.metadata["parameters"]
        assert params["temperature"] == 0.8
        assert params["max_tokens"] == 1500
        assert params["top_p"] == 0.95
        assert params["top_k"] == 50

        # Assert - Timing breakdown
        assert "timing_breakdown" in consolidated.model.metadata
        timing = consolidated.model.metadata["timing_breakdown"]
        assert timing["retrieval_time"] == 0.5
        assert timing["guard_time"] == 0.3
        assert timing["model_time"] == 1.2

        # Assert - Security flags (all scanners passed)
        assert consolidated.guard.details["pii_detected"] is False
        assert consolidated.guard.details["secrets_detected"] is False
        assert consolidated.guard.details["jailbreak_attempt"] is False
        assert consolidated.guard.details["gibberish_detected"] is False
        assert consolidated.guard.details["content_filtered"] is False
        assert len(consolidated.guard.details["blocked_categories"]) == 0

    def test_metrics_cost_accuracy_for_different_models(self):
        """Test that cost estimation is accurate for different model types."""
        # Test data: model_id, tokens_in, tokens_out, expected_total_cost_range
        test_cases = [
            ("gpt-4o-mini", 1_000_000, 1_000_000, (0.75, 0.76)),  # $0.75
            ("gpt-4o", 1_000_000, 1_000_000, (12.49, 12.51)),  # $12.50
            (
                "claude-3-5-sonnet-20241022",
                1_000_000,
                1_000_000,
                (17.99, 18.01),
            ),  # $18.00
            ("gemini-1.5-flash", 1_000_000, 1_000_000, (0.37, 0.38)),  # ~$0.375
        ]

        for model_id, tokens_in, tokens_out, (min_cost, max_cost) in test_cases:
            # Arrange
            llm_response = LLMResponse(
                response="Test",
                model_used=ModelType.QUERY,
                tokens_used=tokens_in + tokens_out,
                processing_time=1.0,
                metadata={
                    "model_id": model_id,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                },
            )

            # Act
            consolidated = self.formatter._consolidate_metrics(
                llm_response=llm_response,
                sources=[],
                retrieval_metrics=None,
                guard_metrics=None,
            )

            # Assert
            total_cost = consolidated.model.metadata["cost_breakdown"]["total_cost"]
            assert min_cost <= total_cost <= max_cost, (
                f"Cost for {model_id} outside expected range: "
                f"{total_cost} not in [{min_cost}, {max_cost}]"
            )

    def test_metrics_without_optional_fields(self):
        """Test that metrics work when optional fields are missing."""
        # Arrange
        llm_response = LLMResponse(
            response="Minimal test",
            model_used=ModelType.QUERY,
            tokens_used=100,
            processing_time=0.5,
            metadata={
                "model_id": "gpt-3.5-turbo",
                "tokens_in": 60,
                "tokens_out": 40,
                # No temperature, max_tokens, or timing
            },
        )

        # Act
        consolidated = self.formatter._consolidate_metrics(
            llm_response=llm_response,
            sources=[],
            retrieval_metrics=None,
            guard_metrics=None,
        )

        # Assert - Basic metrics still work
        assert consolidated.model.metadata["cost_estimate"] is not None
        assert "cost_breakdown" in consolidated.model.metadata

        # Assert - Optional fields handled gracefully
        assert "parameters" not in consolidated.model.metadata  # No temp, so no params
        assert "timing_breakdown" not in consolidated.model.metadata  # No timing

    def test_confidence_score_affected_by_security_risk(self):
        """Test that confidence score is affected by guard risk score."""
        # Arrange - Low risk
        llm_response_safe = LLMResponse(
            response="Safe response",
            model_used=ModelType.QUERY,
            tokens_used=100,
            processing_time=1.0,
            metadata={"model_id": "gpt-4o-mini", "tokens_in": 50, "tokens_out": 50},
        )

        guard_metrics_safe = {
            "risk_score": 0.1,
            "modified": False,
            "details": {"scanners": {}},
        }

        # Arrange - High risk
        llm_response_risky = LLMResponse(
            response="Risky response",
            model_used=ModelType.QUERY,
            tokens_used=100,
            processing_time=1.0,
            metadata={"model_id": "gpt-4o-mini", "tokens_in": 50, "tokens_out": 50},
        )

        guard_metrics_risky = {
            "risk_score": 0.9,
            "modified": True,
            "details": {"scanners": {}},
        }

        # Act
        consolidated_safe = self.formatter._consolidate_metrics(
            llm_response=llm_response_safe,
            sources=[],
            retrieval_metrics=None,
            guard_metrics=guard_metrics_safe,
        )

        consolidated_risky = self.formatter._consolidate_metrics(
            llm_response=llm_response_risky,
            sources=[],
            retrieval_metrics=None,
            guard_metrics=guard_metrics_risky,
        )

        # Assert - Safe response should have higher confidence
        assert consolidated_safe.confidence_score > consolidated_risky.confidence_score
