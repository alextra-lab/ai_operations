"""
Unit tests for TelemetryCapture

Tests the telemetry capture service functionality for Stateless Core v1.
"""

import pytest

from src.orchestrator.app.schemas.run_manifest import ResultKind
from src.orchestrator.app.services.telemetry_capture_service import TelemetryCapture


class TestTelemetryCapture:
    """Test cases for TelemetryCapture."""

    @pytest.fixture
    def telemetry_capture(self):
        """Create a telemetry capture instance for testing."""
        return TelemetryCapture()

    @pytest.fixture
    def sample_params(self):
        """Sample generation parameters for testing."""
        return {
            "temperature": 0.7,
            "max_tokens": 100,
            "top_p": 0.9,
        }

    def test_initialization(self, telemetry_capture):
        """Test telemetry capture initialization."""
        assert telemetry_capture is not None
        assert hasattr(telemetry_capture, "_active_captures")
        assert hasattr(telemetry_capture, "_capture_history")
        assert len(telemetry_capture._active_captures) == 0
        assert len(telemetry_capture._capture_history) == 0

    def test_start_capture(self, telemetry_capture, sample_params):
        """Test starting a telemetry capture."""
        capture_id = "test-capture-1"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-1",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        assert capture_id in telemetry_capture._active_captures
        capture = telemetry_capture._active_captures[capture_id]

        assert capture["use_case_id"] == "test-uc-1"
        assert capture["template_ver"] == "1.0.0"
        assert capture["model_name"] == "gpt-4"
        assert capture["model_version"] == "gpt-4-0613"
        assert capture["params"] == sample_params
        assert capture["start_time"] is not None
        assert capture["llm_start_time"] is None
        assert capture["tools_start_time"] is None
        assert capture["llm_latency_ms"] == 0
        assert capture["tools_latency_ms"] == 0
        assert capture["tokens_in"] == 0
        assert capture["tokens_out"] == 0
        assert capture["tool_chain"] == []
        assert capture["schema_valid"] is False
        assert capture["conformance"] == 0.0
        assert capture["idempotence_ok"] is True
        assert capture["result_kind"] == ResultKind.SUCCESS
        assert capture["errors"] == []

    def test_record_llm_start(self, telemetry_capture, sample_params):
        """Test recording LLM start."""
        capture_id = "test-capture-2"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-2",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        telemetry_capture.record_llm_start(capture_id)

        capture = telemetry_capture._active_captures[capture_id]
        assert capture["llm_start_time"] is not None

    def test_record_llm_end(self, telemetry_capture, sample_params):
        """Test recording LLM end."""
        capture_id = "test-capture-3"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-3",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        telemetry_capture.record_llm_start(capture_id)
        telemetry_capture.record_llm_end(capture_id, tokens_in=1000, tokens_out=500)

        capture = telemetry_capture._active_captures[capture_id]
        assert capture["llm_latency_ms"] >= 0
        assert capture["tokens_in"] == 1000
        assert capture["tokens_out"] == 500

    def test_record_tools_start(self, telemetry_capture, sample_params):
        """Test recording tools start."""
        capture_id = "test-capture-4"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-4",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        telemetry_capture.record_tools_start(capture_id)

        capture = telemetry_capture._active_captures[capture_id]
        assert capture["tools_start_time"] is not None

    def test_record_tools_end(self, telemetry_capture, sample_params):
        """Test recording tools end."""
        capture_id = "test-capture-5"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-5",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        telemetry_capture.record_tools_start(capture_id)
        telemetry_capture.record_tools_end(capture_id)

        capture = telemetry_capture._active_captures[capture_id]
        assert capture["tools_latency_ms"] >= 0

    def test_record_tool_usage(self, telemetry_capture, sample_params):
        """Test recording tool usage."""
        capture_id = "test-capture-6"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-6",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        telemetry_capture.record_tool_usage(capture_id, "tool1")
        telemetry_capture.record_tool_usage(capture_id, "tool2")
        telemetry_capture.record_tool_usage(capture_id, "tool1")  # Duplicate

        capture = telemetry_capture._active_captures[capture_id]
        assert "tool1" in capture["tool_chain"]
        assert "tool2" in capture["tool_chain"]
        assert len(capture["tool_chain"]) == 2  # No duplicates

    def test_record_validation_result(self, telemetry_capture, sample_params):
        """Test recording validation result."""
        capture_id = "test-capture-7"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-7",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        telemetry_capture.record_validation_result(capture_id, schema_valid=True, conformance=0.95)

        capture = telemetry_capture._active_captures[capture_id]
        assert capture["schema_valid"] is True
        assert capture["conformance"] == 0.95

    def test_record_error(self, telemetry_capture, sample_params):
        """Test recording error."""
        capture_id = "test-capture-8"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-8",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        telemetry_capture.record_error(capture_id, "Test error message")

        capture = telemetry_capture._active_captures[capture_id]
        assert capture["result_kind"] == ResultKind.ERROR
        assert "Test error message" in capture["errors"]

    def test_record_policy_block(self, telemetry_capture, sample_params):
        """Test recording policy block."""
        capture_id = "test-capture-9"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-9",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        telemetry_capture.record_policy_block(capture_id, "Content policy violation")

        capture = telemetry_capture._active_captures[capture_id]
        assert capture["result_kind"] == ResultKind.POLICY_BLOCK
        assert "Policy block: Content policy violation" in capture["errors"]

    def test_record_contract_violation(self, telemetry_capture, sample_params):
        """Test recording contract violation."""
        capture_id = "test-capture-10"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-10",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        telemetry_capture.record_contract_violation(capture_id, "Schema validation failed")

        capture = telemetry_capture._active_captures[capture_id]
        assert capture["result_kind"] == ResultKind.CONTRACT_VIOLATION
        assert "Contract violation: Schema validation failed" in capture["errors"]

    def test_record_idempotence_check(self, telemetry_capture, sample_params):
        """Test recording idempotence check."""
        capture_id = "test-capture-11"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-11",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        telemetry_capture.record_idempotence_check(capture_id, False)

        capture = telemetry_capture._active_captures[capture_id]
        assert capture["idempotence_ok"] is False

    def test_finish_capture(self, telemetry_capture, sample_params):
        """Test finishing a telemetry capture."""
        capture_id = "test-capture-12"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-12",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        # Record some activity
        telemetry_capture.record_llm_start(capture_id)
        telemetry_capture.record_llm_end(capture_id, tokens_in=1000, tokens_out=500)
        telemetry_capture.record_tool_usage(capture_id, "tool1")
        telemetry_capture.record_validation_result(capture_id, schema_valid=True, conformance=0.95)

        # Finish capture
        manifest = telemetry_capture.finish_capture(capture_id)

        assert manifest is not None
        assert manifest.use_case_id == "test-uc-12"
        assert manifest.template_ver == "1.0.0"
        assert manifest.model_name == "gpt-4"
        assert manifest.model_version == "gpt-4-0613"
        assert manifest.schema_valid is True
        assert manifest.conformance == 0.95
        assert manifest.tool_chain == ["tool1"]
        assert manifest.tokens_in == 1000
        assert manifest.tokens_out == 500
        assert manifest.result_kind == ResultKind.SUCCESS
        assert len(manifest.params_hash) == 16

        # Check that capture was moved to history and removed from active
        assert capture_id not in telemetry_capture._active_captures
        assert len(telemetry_capture._capture_history) == 1

    def test_finish_capture_nonexistent(self, telemetry_capture):
        """Test finishing a non-existent capture."""
        manifest = telemetry_capture.finish_capture("non-existent-capture")
        assert manifest is None

    def test_get_capture_status(self, telemetry_capture, sample_params):
        """Test getting capture status."""
        capture_id = "test-capture-13"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-13",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        status = telemetry_capture.get_capture_status(capture_id)
        assert status is not None
        assert status["use_case_id"] == "test-uc-13"
        assert status["current_time"] is not None
        assert status["elapsed_ms"] >= 0

        # Test non-existent capture
        status = telemetry_capture.get_capture_status("non-existent")
        assert status is None

    def test_get_capture_history(self, telemetry_capture, sample_params):
        """Test getting capture history."""
        # Start and finish a capture
        capture_id = "test-capture-14"
        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-14",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )
        telemetry_capture.finish_capture(capture_id)

        history = telemetry_capture.get_capture_history()
        assert len(history) == 1
        assert history[0]["use_case_id"] == "test-uc-14"

        # Test with limit
        history_limited = telemetry_capture.get_capture_history(limit=1)
        assert len(history_limited) == 1

    def test_clear_history(self, telemetry_capture, sample_params):
        """Test clearing capture history."""
        # Add some history
        capture_id = "test-capture-15"
        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-15",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )
        telemetry_capture.finish_capture(capture_id)

        assert len(telemetry_capture._capture_history) == 1

        telemetry_capture.clear_history()
        assert len(telemetry_capture._capture_history) == 0

    def test_get_active_captures(self, telemetry_capture, sample_params):
        """Test getting active captures."""
        # Start some captures
        capture_id1 = "test-capture-16"
        capture_id2 = "test-capture-17"

        telemetry_capture.start_capture(
            capture_id=capture_id1,
            use_case_id="test-uc-16",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        telemetry_capture.start_capture(
            capture_id=capture_id2,
            use_case_id="test-uc-17",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        active_captures = telemetry_capture.get_active_captures()
        assert len(active_captures) == 2
        assert capture_id1 in active_captures
        assert capture_id2 in active_captures

    def test_cancel_capture(self, telemetry_capture, sample_params):
        """Test cancelling a capture."""
        capture_id = "test-capture-18"

        telemetry_capture.start_capture(
            capture_id=capture_id,
            use_case_id="test-uc-18",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )

        assert capture_id in telemetry_capture._active_captures

        # Cancel the capture
        cancelled = telemetry_capture.cancel_capture(capture_id)
        assert cancelled is True
        assert capture_id not in telemetry_capture._active_captures

        # Try to cancel non-existent capture
        cancelled = telemetry_capture.cancel_capture("non-existent")
        assert cancelled is False

    def test_get_telemetry_stats(self, telemetry_capture, sample_params):
        """Test getting telemetry statistics."""
        # Initially no stats
        stats = telemetry_capture.get_telemetry_stats()
        assert stats["total_captures"] == 0
        assert stats["active_captures"] == 0
        assert stats["avg_latency_ms"] == 0
        assert stats["success_rate"] == 0
        assert stats["error_rate"] == 0

        # Add some captures
        capture_id1 = "test-capture-19"
        capture_id2 = "test-capture-20"

        # Successful capture
        telemetry_capture.start_capture(
            capture_id=capture_id1,
            use_case_id="test-uc-19",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )
        telemetry_capture.finish_capture(capture_id1)

        # Error capture
        telemetry_capture.start_capture(
            capture_id=capture_id2,
            use_case_id="test-uc-20",
            template_ver="1.0.0",
            model_name="gpt-4",
            model_version="gpt-4-0613",
            params=sample_params,
        )
        telemetry_capture.record_error(capture_id2, "Test error")
        telemetry_capture.finish_capture(capture_id2)

        stats = telemetry_capture.get_telemetry_stats()
        assert stats["total_captures"] == 2
        assert stats["active_captures"] == 0
        assert stats["avg_latency_ms"] >= 0
        assert stats["success_rate"] == 0.5  # 1 success out of 2
        assert stats["error_rate"] == 0.5  # 1 error out of 2

    def test_generate_params_hash(self, telemetry_capture):
        """Test parameter hash generation."""
        params1 = {"temperature": 0.7, "max_tokens": 100}
        params2 = {
            "max_tokens": 100,
            "temperature": 0.7,
        }  # Same params, different order
        params3 = {"temperature": 0.8, "max_tokens": 100}  # Different params

        hash1 = telemetry_capture._generate_params_hash(params1)
        hash2 = telemetry_capture._generate_params_hash(params2)
        hash3 = telemetry_capture._generate_params_hash(params3)

        # Same parameters should generate same hash regardless of order
        assert hash1 == hash2
        # Different parameters should generate different hash
        assert hash1 != hash3
        # Hash should be 16 characters
        assert len(hash1) == 16
        assert len(hash2) == 16
        assert len(hash3) == 16
