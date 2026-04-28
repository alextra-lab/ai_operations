"""
Unit tests for TelemetryIntegration service.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.orchestrator.app.schemas.run_manifest import ResultKind
from src.orchestrator.app.services.telemetry_integration_service import TelemetryIntegration


class TestTelemetryIntegration:
    """Test cases for TelemetryIntegration service."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def telemetry_integration(self, mock_db_session):
        """Create a TelemetryIntegration instance."""
        return TelemetryIntegration(mock_db_session)

    def test_initialization(self, telemetry_integration, mock_db_session):
        """Test service initialization."""
        assert telemetry_integration.db_session == mock_db_session
        assert telemetry_integration.telemetry_capture is not None
        assert telemetry_integration.run_manifest_service is not None

    def test_start_execution_capture(self, telemetry_integration):
        """Test starting execution capture."""
        request_id = "test-request-123"
        use_case_id = "test-use-case"
        template_ver = "1.0"
        model_name = "gpt-4"
        model_version = "1.0"
        params = {"temperature": 0.7, "max_tokens": 1000}

        # Should not raise any exceptions
        telemetry_integration.start_execution_capture(
            request_id=request_id,
            use_case_id=use_case_id,
            template_ver=template_ver,
            model_name=model_name,
            model_version=model_version,
            params=params,
        )

    def test_record_llm_start(self, telemetry_integration):
        """Test recording LLM start."""
        request_id = "test-request-123"

        # Should not raise any exceptions
        telemetry_integration.record_llm_start(request_id)

    def test_record_llm_end(self, telemetry_integration):
        """Test recording LLM end."""
        request_id = "test-request-123"
        tokens_in = 100
        tokens_out = 50
        processing_time_ms = 1500

        # Should not raise any exceptions
        telemetry_integration.record_llm_end(
            request_id=request_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            processing_time_ms=processing_time_ms,
        )

    def test_record_tools_start(self, telemetry_integration):
        """Test recording tools start."""
        request_id = "test-request-123"

        # Should not raise any exceptions
        telemetry_integration.record_tools_start(request_id)

    def test_record_tools_end(self, telemetry_integration):
        """Test recording tools end."""
        request_id = "test-request-123"
        tool_chain = ["search", "analyze"]
        processing_time_ms = 500

        # Should not raise any exceptions
        telemetry_integration.record_tools_end(
            request_id=request_id,
            tool_chain=tool_chain,
            processing_time_ms=processing_time_ms,
        )

    def test_record_validation_result(self, telemetry_integration):
        """Test recording validation result."""
        request_id = "test-request-123"
        schema_valid = True
        conformance = 0.95

        # Should not raise any exceptions
        telemetry_integration.record_validation_result(
            request_id=request_id,
            schema_valid=schema_valid,
            conformance=conformance,
        )

    def test_record_error(self, telemetry_integration):
        """Test recording error."""
        request_id = "test-request-123"
        error_message = "Test error"

        # Should not raise any exceptions
        telemetry_integration.record_error(request_id, error_message)

    def test_record_policy_block(self, telemetry_integration):
        """Test recording policy block."""
        request_id = "test-request-123"
        reason = "Content policy violation"

        # Should not raise any exceptions
        telemetry_integration.record_policy_block(request_id, reason)

    def test_record_contract_violation(self, telemetry_integration):
        """Test recording contract violation."""
        request_id = "test-request-123"
        violation = "Output format violation"

        # Should not raise any exceptions
        telemetry_integration.record_contract_violation(request_id, violation)

    def test_record_idempotence_check(self, telemetry_integration):
        """Test recording idempotence check."""
        request_id = "test-request-123"
        is_idempotent = True

        # Should not raise any exceptions
        telemetry_integration.record_idempotence_check(request_id, is_idempotent)

    @pytest.mark.asyncio
    async def test_finish_execution_capture_success(self, telemetry_integration):
        """Test finishing execution capture successfully."""
        request_id = "test-request-123"

        # Mock the telemetry capture finish_capture method
        mock_capture_data = {
            "use_case_id": "test-use-case",
            "template_ver": "1.0",
            "model_name": "gpt-4",
            "model_version": "1.0",
            "params_hash": "abc123",
            "schema_valid": True,
            "conformance": 0.95,
            "tool_chain": ["search"],
            "idempotence_ok": True,
            "latency_total_ms": 2000,
            "latency_llm_ms": 1500,
            "latency_tools_ms": 500,
            "tokens_in": 100,
            "tokens_out": 50,
        }

        telemetry_integration.telemetry_capture.finish_capture = MagicMock(
            return_value=mock_capture_data
        )

        # Mock the run manifest service
        mock_run_manifest = MagicMock()
        telemetry_integration.run_manifest_service.create_manifest_from_execution = AsyncMock(
            return_value=mock_run_manifest
        )

        result = await telemetry_integration.finish_execution_capture(
            request_id=request_id,
            result_kind=ResultKind.SUCCESS,
        )

        assert result == mock_run_manifest
        telemetry_integration.telemetry_capture.finish_capture.assert_called_once_with(request_id)
        telemetry_integration.run_manifest_service.create_manifest_from_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_finish_execution_capture_no_data(self, telemetry_integration):
        """Test finishing execution capture when no capture data exists."""
        request_id = "test-request-123"

        # Mock the telemetry capture finish_capture method to return None
        telemetry_integration.telemetry_capture.finish_capture = MagicMock(return_value=None)

        result = await telemetry_integration.finish_execution_capture(
            request_id=request_id,
            result_kind=ResultKind.SUCCESS,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_finish_execution_capture_exception(self, telemetry_integration):
        """Test finishing execution capture when an exception occurs."""
        request_id = "test-request-123"

        # Mock the telemetry capture finish_capture method to raise an exception
        telemetry_integration.telemetry_capture.finish_capture = MagicMock(
            side_effect=Exception("Test error")
        )

        result = await telemetry_integration.finish_execution_capture(
            request_id=request_id,
            result_kind=ResultKind.SUCCESS,
        )

        assert result is None

    def test_get_capture_status(self, telemetry_integration):
        """Test getting capture status."""
        request_id = "test-request-123"

        # Mock the telemetry capture get_capture_status method
        mock_status = {"status": "active", "start_time": 1234567890}
        telemetry_integration.telemetry_capture.get_capture_status = MagicMock(
            return_value=mock_status
        )

        result = telemetry_integration.get_capture_status(request_id)

        assert result == mock_status
        telemetry_integration.telemetry_capture.get_capture_status.assert_called_once_with(
            request_id
        )

    def test_cancel_capture(self, telemetry_integration):
        """Test canceling capture."""
        request_id = "test-request-123"

        # Mock the telemetry capture cancel_capture method
        telemetry_integration.telemetry_capture.cancel_capture = MagicMock()

        telemetry_integration.cancel_capture(request_id)

        telemetry_integration.telemetry_capture.cancel_capture.assert_called_once_with(request_id)
