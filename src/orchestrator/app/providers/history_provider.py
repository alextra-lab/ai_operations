"""
History provider interfaces and implementations.

Defines the HistoryProvider protocol and provides no-op implementation
for stateless v1 architecture (ADR-030).
"""

from typing import Any, Protocol
from uuid import UUID


class HistoryProvider(Protocol):
    """
    Protocol for history persistence.

    In stateless v1, history lives on client edge (ADR-030).
    In future stateful v2+, this enables GovernedHistory provider.
    """

    async def append(self, run_id: UUID, payload: dict[str, Any]) -> None:
        """
        Append a history entry.

        Args:
            run_id: Unique run identifier
            payload: History payload (conversation data)
        """
        ...

    async def fetch(
        self,
        case_id: str | None = None,
        run_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch history entries.

        Args:
            case_id: Optional use case filter
            run_id: Optional run ID filter

        Returns:
            List of history entries
        """
        ...


class EdgeOnlyHistory:
    """
    No-op history provider for stateless v1.

    This implementation satisfies the HistoryProvider protocol but does
    not persist any data server-side. All conversation history lives on
    the client edge with TTL-based expiration.

    ADR-030: No Transcripts; Run Manifests Only
    """

    async def append(self, run_id: UUID, payload: dict[str, Any]) -> None:
        """
        No-op: history lives on client edge.

        In stateless architecture, conversation history is managed by the
        client (browser SessionStorage or IndexedDB) and expires based on
        configurable TTL (default: 24 hours).
        """
        # No-op: Intentionally empty for stateless v1

    async def fetch(
        self,
        _case_id: str | None = None,
        _run_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        No-op: return empty list.

        Client is responsible for maintaining and providing conversation
        history when making requests. Server does not store or retrieve
        conversation data.

        Args:
            case_id: Unused in stateless mode
            run_id: Unused in stateless mode
        """
        return []
