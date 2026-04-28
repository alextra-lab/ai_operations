"""
Edge-Only History Provider for Stateless Core v1

This provider implements the HistoryProvider protocol but doesn't store
conversation history server-side. History lives on the client edge with
TTL-based expiration.

This aligns with ADR-030 (No Transcripts; Run Manifests Only) for the
stateless architecture.
"""

from typing import Any
from uuid import UUID

from shared.logging_utils.fastapi import get_logger

logger = get_logger(__name__)


class EdgeOnlyHistory:
    """
    No-op history provider for stateless v1.

    This provider doesn't store conversation history server-side.
    History lives on the client edge with TTL-based expiration.
    """

    def __init__(self) -> None:
        """Initialize the edge-only history provider."""
        self.provider_type = "edge_only"
        self.enabled = True
        logger.info("Initialized EdgeOnlyHistory provider (no server-side storage)")

    async def append(self, run_id: UUID, _payload: dict[str, Any]) -> None:
        """
        No-op: history lives on client edge.

        Args:
            run_id: Unique identifier for the run
            _payload: History entry data (ignored)
        """
        logger.debug(f"EdgeOnlyHistory.append called for run_id={run_id} (no-op)")
        # No-op: history is managed on client edge

    async def fetch(
        self, case_id: str | None = None, run_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        """
        No-op: return empty list.

        Args:
            case_id: Use case ID (ignored)
            run_id: Run ID (ignored)

        Returns:
            Empty list (no server-side history)
        """
        logger.debug(f"EdgeOnlyHistory.fetch called for case_id={case_id}, run_id={run_id} (no-op)")
        # No-op: return empty list since no server-side history
        return []

    async def health_check(self) -> dict[str, Any]:
        """
        Health check for the provider.

        Returns:
            Health status information
        """
        return {
            "provider_type": self.provider_type,
            "enabled": self.enabled,
            "healthy": True,
            "message": "Edge-only history provider (no server-side storage)",
        }

    async def get_stats(self) -> dict[str, Any]:
        """
        Get provider statistics.

        Returns:
            Statistics (always empty for no-op provider)
        """
        return {
            "provider_type": self.provider_type,
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "avg_response_time_ms": 0.0,
            "error_rate": 0.0,
        }

    def __str__(self) -> str:
        """String representation of the provider."""
        return f"EdgeOnlyHistory(provider_type={self.provider_type}, enabled={self.enabled})"

    def __repr__(self) -> str:
        """Detailed string representation of the provider."""
        return f"EdgeOnlyHistory(provider_type='{self.provider_type}', enabled={self.enabled})"
