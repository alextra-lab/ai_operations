"""
Provider Services for Stateless Core v1

This module provides pluggable provider implementations for the stateless architecture.
For v1, all providers are no-op implementations that don't store data.

Providers:
- HistoryProvider: Conversation history persistence
- EvidenceSink: Evidence storage and retrieval
- CryptoProvider: Cryptographic operations

Factory function creates appropriate providers based on configuration.
"""

from typing import Any, Protocol
from uuid import UUID

from .edge_only_history import EdgeOnlyHistory
from .no_crypto import NoCrypto
from .none_evidence import NoneEvidence


class HistoryProvider(Protocol):
    """Protocol for history persistence providers."""

    async def append(self, run_id: UUID, payload: dict[str, Any], /) -> None:
        """Append history entry."""
        ...

    async def fetch(
        self, case_id: str | None = None, run_id: UUID | None = None
    ) -> list[dict[str, Any]]:
        """Fetch history entries."""
        ...


class EvidenceSink(Protocol):
    """Protocol for evidence storage providers."""

    async def store(self, evidence: dict[str, Any], /) -> str:
        """Store evidence, return ID."""
        ...

    async def retrieve(self, evidence_id: str) -> dict[str, Any]:
        """Retrieve evidence by ID."""
        ...


class CryptoProvider(Protocol):
    """Protocol for cryptographic operation providers."""

    async def encrypt(self, data: str) -> str:
        """Encrypt data."""
        ...

    async def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        ...


def create_providers() -> tuple[HistoryProvider, EvidenceSink, CryptoProvider]:
    """
    Create providers based on configuration.

    For v1, always returns no-op providers since stateless architecture
    doesn't store conversation data server-side.

    Returns:
        Tuple of (history_provider, evidence_sink, crypto_provider)
    """
    # For v1, always use no-op providers
    history_provider: HistoryProvider = EdgeOnlyHistory()
    evidence_sink: EvidenceSink = NoneEvidence()
    crypto_provider: CryptoProvider = NoCrypto()

    return history_provider, evidence_sink, crypto_provider


def create_history_provider(provider_type: str = "none") -> HistoryProvider:
    """Create a history provider based on type."""
    if provider_type == "none":
        return EdgeOnlyHistory()
    # Future: return governed provider
    return EdgeOnlyHistory()


def create_evidence_sink(sink_type: str = "none") -> EvidenceSink:
    """Create an evidence sink based on type."""
    if sink_type == "none":
        return NoneEvidence()
    # Future: return governed sink
    return NoneEvidence()


def create_crypto_provider(provider_type: str = "none") -> CryptoProvider:
    """Create a crypto provider based on type."""
    if provider_type == "none":
        return NoCrypto()
    # Future: return governed provider
    return NoCrypto()


__all__ = [
    "CryptoProvider",
    "EdgeOnlyHistory",
    "EvidenceSink",
    "HistoryProvider",
    "NoCrypto",
    "NoneEvidence",
    "create_crypto_provider",
    "create_evidence_sink",
    "create_history_provider",
    "create_providers",
]
