"""
Telemetry Capture Service for Stateless Core v1

This module implements the telemetry capture service for collecting
execution metrics without storing conversation content (ADR-030).

Provides in-memory telemetry collection for run manifests.
"""

import time
from typing import Any

from ..schemas.run_manifest import (
    ResultKind,
    RunManifestCreate,
)


class TelemetryCapture:
    """In-memory telemetry collector for run manifests."""

    def __init__(self) -> None:
        """Initialize the telemetry capture service."""
        self._active_captures: dict[str, dict[str, Any]] = {}
        self._capture_history: list[dict[str, Any]] = []

    def start_capture(
        self,
        capture_id: str,
        use_case_id: str,
        template_ver: str,
        model_name: str,
        model_version: str,
        params: dict[str, Any],
    ) -> None:
        """
        Start telemetry capture for an execution.

        Args:
            capture_id: Unique identifier for this capture
            use_case_id: Use case identifier
            template_ver: Template version
            model_name: Model name
            model_version: Model version
            params: Generation parameters
        """
        start_time = time.time()

        self._active_captures[capture_id] = {
            "use_case_id": use_case_id,
            "template_ver": template_ver,
            "model_name": model_name,
            "model_version": model_version,
            "params": params,
            "start_time": start_time,
            "llm_start_time": None,
            "tools_start_time": None,
            "llm_latency_ms": 0,
            "tools_latency_ms": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "tool_chain": [],
            "schema_valid": False,
            "conformance": 0.0,
            "idempotence_ok": True,
            "result_kind": ResultKind.SUCCESS,
            "errors": [],
        }

    def record_llm_start(self, capture_id: str) -> None:
        """
        Record the start of LLM processing.

        Args:
            capture_id: Capture identifier
        """
        if capture_id in self._active_captures:
            self._active_captures[capture_id]["llm_start_time"] = time.time()

    def record_llm_end(
        self,
        capture_id: str,
        tokens_in: int,
        tokens_out: int,
    ) -> None:
        """
        Record the end of LLM processing.

        Args:
            capture_id: Capture identifier
            tokens_in: Input tokens consumed
            tokens_out: Output tokens generated
        """
        if capture_id in self._active_captures:
            capture = self._active_captures[capture_id]
            if capture["llm_start_time"]:
                llm_latency = (time.time() - capture["llm_start_time"]) * 1000
                capture["llm_latency_ms"] = int(llm_latency)

            capture["tokens_in"] = tokens_in
            capture["tokens_out"] = tokens_out

    def record_tools_start(self, capture_id: str) -> None:
        """
        Record the start of tool processing.

        Args:
            capture_id: Capture identifier
        """
        if capture_id in self._active_captures:
            self._active_captures[capture_id]["tools_start_time"] = time.time()

    def record_tools_end(self, capture_id: str) -> None:
        """
        Record the end of tool processing.

        Args:
            capture_id: Capture identifier
        """
        if capture_id in self._active_captures:
            capture = self._active_captures[capture_id]
            if capture["tools_start_time"]:
                tools_latency = (time.time() - capture["tools_start_time"]) * 1000
                capture["tools_latency_ms"] = int(tools_latency)

    def record_tool_usage(self, capture_id: str, tool_name: str) -> None:
        """
        Record the use of a tool.

        Args:
            capture_id: Capture identifier
            tool_name: Name of the tool used
        """
        if (
            capture_id in self._active_captures
            and tool_name not in self._active_captures[capture_id]["tool_chain"]
        ):
            self._active_captures[capture_id]["tool_chain"].append(tool_name)

    def record_validation_result(
        self,
        capture_id: str,
        schema_valid: bool,
        conformance: float,
    ) -> None:
        """
        Record schema validation results.

        Args:
            capture_id: Capture identifier
            schema_valid: Whether schema validation passed
            conformance: Conformance score (0-1)
        """
        if capture_id in self._active_captures:
            self._active_captures[capture_id]["schema_valid"] = schema_valid
            self._active_captures[capture_id]["conformance"] = conformance

    def record_error(self, capture_id: str, error: str) -> None:
        """
        Record an error during execution.

        Args:
            capture_id: Capture identifier
            error: Error message
        """
        if capture_id in self._active_captures:
            self._active_captures[capture_id]["errors"].append(error)
            self._active_captures[capture_id]["result_kind"] = ResultKind.ERROR

    def record_policy_block(self, capture_id: str, reason: str) -> None:
        """
        Record a policy block.

        Args:
            capture_id: Capture identifier
            reason: Reason for policy block
        """
        if capture_id in self._active_captures:
            self._active_captures[capture_id]["result_kind"] = ResultKind.POLICY_BLOCK
            self._active_captures[capture_id]["errors"].append(f"Policy block: {reason}")

    def record_contract_violation(self, capture_id: str, reason: str) -> None:
        """
        Record a contract violation.

        Args:
            capture_id: Capture identifier
            reason: Reason for contract violation
        """
        if capture_id in self._active_captures:
            self._active_captures[capture_id]["result_kind"] = ResultKind.CONTRACT_VIOLATION
            self._active_captures[capture_id]["errors"].append(f"Contract violation: {reason}")

    def record_idempotence_check(self, capture_id: str, is_idempotent: bool) -> None:
        """
        Record idempotence check result.

        Args:
            capture_id: Capture identifier
            is_idempotent: Whether execution was idempotent
        """
        if capture_id in self._active_captures:
            self._active_captures[capture_id]["idempotence_ok"] = is_idempotent

    def finish_capture(self, capture_id: str) -> RunManifestCreate | None:
        """
        Finish telemetry capture and create run manifest.

        Args:
            capture_id: Capture identifier

        Returns:
            Run manifest create schema if capture exists, None otherwise
        """
        if capture_id not in self._active_captures:
            return None

        capture = self._active_captures[capture_id]
        end_time = time.time()
        total_latency = int((end_time - capture["start_time"]) * 1000)

        import uuid as uuid_lib

        # Create run manifest
        manifest = RunManifestCreate(
            run_id=(uuid_lib.UUID(capture_id) if isinstance(capture_id, str) else capture_id),
            use_case_id=capture["use_case_id"],
            template_ver=capture["template_ver"],
            model_name=capture["model_name"],
            model_version=capture["model_version"],
            generation_params=capture["params"],
            schema_valid=capture["schema_valid"],
            conformance=capture["conformance"],
            tool_chain=capture["tool_chain"],
            idempotence_ok=capture["idempotence_ok"],
            latency_total_ms=total_latency,
            latency_llm_ms=capture["llm_latency_ms"],
            latency_tools_ms=capture["tools_latency_ms"],
            tokens_in=capture["tokens_in"],
            tokens_out=capture["tokens_out"],
            result_kind=capture["result_kind"],
        )

        # Store in history and clean up
        capture["end_time"] = end_time
        capture["total_latency_ms"] = total_latency
        self._capture_history.append(capture.copy())
        del self._active_captures[capture_id]

        return manifest

    def get_capture_status(self, capture_id: str) -> dict[str, Any] | None:
        """
        Get the current status of a capture.

        Args:
            capture_id: Capture identifier

        Returns:
            Capture status dictionary if found, None otherwise
        """
        if capture_id not in self._active_captures:
            return None

        capture = self._active_captures[capture_id].copy()
        current_time = time.time()
        capture["current_time"] = current_time
        capture["elapsed_ms"] = int((current_time - capture["start_time"]) * 1000)

        return capture

    def get_capture_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get capture history.

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List of capture history entries
        """
        return self._capture_history[-limit:]

    def clear_history(self) -> None:
        """Clear capture history."""
        self._capture_history.clear()

    def get_active_captures(self) -> list[str]:
        """
        Get list of active capture IDs.

        Returns:
            List of active capture IDs
        """
        return list(self._active_captures.keys())

    def cancel_capture(self, capture_id: str) -> bool:
        """
        Cancel an active capture.

        Args:
            capture_id: Capture identifier

        Returns:
            True if capture was cancelled, False if not found
        """
        if capture_id in self._active_captures:
            del self._active_captures[capture_id]
            return True
        return False

    @staticmethod
    def _generate_params_hash(params: dict[str, Any]) -> str:
        """
        Generate a hash for generation parameters.

        Args:
            params: Generation parameters dictionary

        Returns:
            Hash string for the parameters
        """
        import hashlib
        import json

        # Sort parameters for consistent hashing
        sorted_params = sorted(params.items())
        params_str = json.dumps(sorted_params, sort_keys=True)
        return hashlib.sha256(params_str.encode()).hexdigest()[:16]

    def get_telemetry_stats(self) -> dict[str, Any]:
        """
        Get telemetry capture statistics.

        Returns:
            Statistics dictionary
        """
        total_captures = len(self._capture_history)
        active_captures = len(self._active_captures)

        if total_captures == 0:
            return {
                "total_captures": 0,
                "active_captures": active_captures,
                "avg_latency_ms": 0,
                "success_rate": 0,
                "error_rate": 0,
            }

        # Calculate statistics from history
        latencies = [c.get("total_latency_ms", 0) for c in self._capture_history]
        result_kinds = [c.get("result_kind", "error") for c in self._capture_history]

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        success_count = sum(1 for kind in result_kinds if kind == "success")
        error_count = sum(1 for kind in result_kinds if kind == "error")

        return {
            "total_captures": total_captures,
            "active_captures": active_captures,
            "avg_latency_ms": avg_latency,
            "success_rate": success_count / total_captures,
            "error_rate": error_count / total_captures,
        }
