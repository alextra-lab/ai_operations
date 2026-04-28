"""
Evidence sink interfaces and implementations.

Defines the EvidenceSink protocol and provides no-op implementation
for stateless v1 architecture (ADR-033).
"""

from typing import Any, Protocol


class EvidenceSink(Protocol):
    """
    Protocol for evidence storage.

    In stateless v1, evidence collection is disabled (ADR-033).
    In future stateful v2+, this enables WormEvidence provider.
    """

    async def store(self, evidence: dict[str, Any]) -> str:
        """
        Store evidence and return ID.

        Args:
            evidence: Evidence data to store

        Returns:
            Evidence ID
        """
        ...

    async def retrieve(self, evidence_id: str) -> dict[str, Any]:
        """
        Retrieve evidence by ID.

        Args:
            evidence_id: Evidence identifier

        Returns:
            Evidence data
        """
        ...


class NoneEvidence:
    """
    No-op evidence sink for stateless v1.

    This implementation satisfies the EvidenceSink protocol but does
    not persist any evidence server-side. Evidence collection is disabled
    to reduce security scope and compliance burden.

    ADR-033: Provider Interfaces (Disabled for v1)
    """

    async def store(self, _evidence: dict[str, Any]) -> str:
        """
        No-op: return dummy ID.

        Evidence collection is disabled in stateless architecture.
        For forensic evidence preservation, use v2+ WormEvidence provider.
        """
        return "none"

    async def retrieve(self, _evidence_id: str) -> dict[str, Any]:
        """
        No-op: return empty dict.

        Evidence retrieval is not supported in stateless v1.
        """
        return {}
