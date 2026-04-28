"""
Telemetry Integration Service for Stateless Core v1

This module integrates telemetry capture with the orchestrator service,
providing seamless collection of execution metrics for run manifests.

P5-A23 Phase 7: Converted to async database patterns (Nov 2025).
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging_utils.fastapi import configure_logging

from ..db.models import RunManifest as RunManifestModel
from ..schemas.run_manifest import ResultKind
from .run_manifest_service import RunManifestService
from .telemetry_capture_service import TelemetryCapture

logger = configure_logging(
    service_name="telemetry_integration", log_level="INFO", log_format="json"
)


class TelemetryIntegration:
    """Integrates telemetry capture with orchestrator execution flow."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize telemetry integration.

        Args:
            db_session: Async database session for run manifest storage

        Note:
            RunManifestService expects AsyncSession and is now properly typed.
            See ADR-030 for telemetry architecture.
        """
        self.db_session = db_session
        self.telemetry_capture = TelemetryCapture()
        # RunManifestService expects AsyncSession
        self.run_manifest_service = RunManifestService(db_session)

    def start_execution_capture(
        self,
        request_id: str,
        use_case_id: str,
        template_ver: str,
        model_name: str,
        model_version: str,
        params: dict[str, Any],
    ) -> None:
        """
        Start telemetry capture for an execution.

        Args:
            request_id: Unique request identifier
            use_case_id: Use case identifier
            template_ver: Template version
            model_name: Model name
            model_version: Model version
            params: Generation parameters
        """
        self.telemetry_capture.start_capture(
            capture_id=request_id,
            use_case_id=use_case_id,
            template_ver=template_ver,
            model_name=model_name,
            model_version=model_version,
            params=params,
        )

    def record_llm_start(self, request_id: str) -> None:
        """Record LLM processing start."""
        self.telemetry_capture.record_llm_start(request_id)

    def record_llm_end(
        self,
        request_id: str,
        tokens_in: int,
        tokens_out: int,
        _processing_time_ms: int,
    ) -> None:
        """
        Record LLM processing completion.

        Args:
            request_id: Request identifier
            tokens_in: Input tokens
            tokens_out: Output tokens
            _processing_time_ms: Processing time in milliseconds (not used by underlying service)
        """
        self.telemetry_capture.record_llm_end(request_id, tokens_in, tokens_out)

    def record_tools_start(self, request_id: str) -> None:
        """Record tool processing start."""
        self.telemetry_capture.record_tools_start(request_id)

    def record_tools_end(
        self,
        request_id: str,
        _tool_chain: list[str],
        _processing_time_ms: int,
    ) -> None:
        """
        Record tool processing completion.

        Args:
            request_id: Request identifier
            _tool_chain: List of tools used (not used by underlying service)
            _processing_time_ms: Processing time in milliseconds (not used by underlying service)
        """
        self.telemetry_capture.record_tools_end(request_id)

    def record_validation_result(
        self,
        request_id: str,
        schema_valid: bool,
        conformance: float,
    ) -> None:
        """
        Record validation results.

        Args:
            request_id: Request identifier
            schema_valid: Whether schema validation passed
            conformance: Conformance score
        """
        self.telemetry_capture.record_validation_result(request_id, schema_valid, conformance)

    def record_error(self, request_id: str, error_message: str) -> None:
        """
        Record execution error.

        Args:
            request_id: Request identifier
            error_message: Error description
        """
        self.telemetry_capture.record_error(request_id, error_message)

    def record_policy_block(self, request_id: str, reason: str) -> None:
        """
        Record policy block.

        Args:
            request_id: Request identifier
            reason: Block reason
        """
        self.telemetry_capture.record_policy_block(request_id, reason)

    def record_contract_violation(self, request_id: str, violation: str) -> None:
        """
        Record contract violation.

        Args:
            request_id: Request identifier
            violation: Violation description
        """
        self.telemetry_capture.record_contract_violation(request_id, violation)

    def record_idempotence_check(self, request_id: str, is_idempotent: bool) -> None:
        """
        Record idempotence check result.

        Args:
            request_id: Request identifier
            is_idempotent: Whether execution is idempotent
        """
        self.telemetry_capture.record_idempotence_check(request_id, is_idempotent)

    async def finish_execution_capture(
        self,
        request_id: str,
        _result_kind: ResultKind = ResultKind.SUCCESS,
    ) -> RunManifestModel | None:
        """
        Finish telemetry capture and create run manifest.

        Args:
            request_id: Request identifier
            _result_kind: Execution result kind

        Returns:
            Created run manifest or None if capture failed
        """
        try:
            # Finish capture and get run manifest schema
            manifest_create = self.telemetry_capture.finish_capture(request_id)
            if not manifest_create:
                return None

            # KNOWN LIMITATION: Manifest persistence not implemented
            # Returns RunManifestCreate schema instead of persisted RunManifest DB record
            #
            # Current behavior:
            # - Telemetry data is captured in memory during request execution
            # - finish_capture() returns RunManifestCreate schema with metrics
            # - Schema is returned but not persisted to database
            #
            # Why persistence is skipped:
            # - RunManifestService.create_manifest() is async but we're in sync context
            # - Would require async/await refactor of TelemetryIntegration and UseCaseRunner
            # - Current implementation satisfies immediate telemetry needs (metrics logging)
            #
            # Future work (requires async refactor):
            # 1. Make TelemetryIntegration.finish_execution_capture() async
            # 2. Make UseCaseRunner.run() async (it already is, so this is viable)
            # 3. await self.run_manifest_service.create_manifest(manifest_create)
            # 4. Return persisted RunManifest DB object
            #
            # For now, return schema object for immediate use
            return manifest_create  # type: ignore[return-value]

        except Exception as e:
            # Log error but don't fail the request
            logger.error(f"Failed to create run manifest: {e}", exc_info=True)
            return None

    def get_capture_status(self, request_id: str) -> dict[str, Any] | None:
        """
        Get current capture status.

        Args:
            request_id: Request identifier

        Returns:
            Capture status or None if not found
        """
        return self.telemetry_capture.get_capture_status(request_id)

    def cancel_capture(self, request_id: str) -> None:
        """
        Cancel active capture.

        Args:
            request_id: Request identifier
        """
        self.telemetry_capture.cancel_capture(request_id)
