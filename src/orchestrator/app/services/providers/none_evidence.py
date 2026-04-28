"""
None Evidence Sink for Stateless Core v1

This provider implements the EvidenceSink protocol but doesn't store
evidence server-side. Evidence storage is deferred to future stateful
capabilities.

This aligns with ADR-033 (Provider Interfaces) for the stateless architecture.
"""

from typing import Any
from uuid import uuid4

from shared.logging_utils.fastapi import get_logger

logger = get_logger(__name__)


class NoneEvidence:
    """
    No-op evidence sink for stateless v1.

    This provider doesn't store evidence server-side.
    Evidence storage is deferred to future stateful capabilities.
    """

    def __init__(self) -> None:
        """Initialize the none evidence sink."""
        self.sink_type = "none"
        self.enabled = True
        logger.info("Initialized NoneEvidence sink (no server-side storage)")

    async def store(self, _evidence: dict[str, Any]) -> str:
        """
        No-op: return dummy ID.

        Args:
            _evidence: Evidence data (ignored)

        Returns:
            Dummy evidence ID
        """
        evidence_id = f"none_{uuid4().hex[:8]}"
        logger.debug(f"NoneEvidence.store called (no-op), returning dummy ID: {evidence_id}")
        # No-op: return dummy ID since no server-side storage
        return evidence_id

    async def retrieve(self, evidence_id: str) -> dict[str, Any]:
        """
        No-op: return empty dict.

        Args:
            evidence_id: Evidence ID (ignored)

        Returns:
            Empty dict (no server-side evidence)
        """
        logger.debug(f"NoneEvidence.retrieve called for evidence_id={evidence_id} (no-op)")
        # No-op: return empty dict since no server-side evidence
        return {}

    async def health_check(self) -> dict[str, Any]:
        """
        Health check for the sink.

        Returns:
            Health status information
        """
        return {
            "sink_type": self.sink_type,
            "enabled": self.enabled,
            "healthy": True,
            "message": "None evidence sink (no server-side storage)",
        }

    async def get_stats(self) -> dict[str, Any]:
        """
        Get sink statistics.

        Returns:
            Statistics (always empty for no-op sink)
        """
        return {
            "sink_type": self.sink_type,
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "avg_response_time_ms": 0.0,
            "error_rate": 0.0,
        }

    def __str__(self) -> str:
        """String representation of the sink."""
        return f"NoneEvidence(sink_type={self.sink_type}, enabled={self.enabled})"

    def __repr__(self) -> str:
        """Detailed string representation of the sink."""
        return f"NoneEvidence(sink_type='{self.sink_type}', enabled={self.enabled})"
