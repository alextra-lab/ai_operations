"""
Provider interfaces for stateless architecture.

This module defines abstract provider interfaces for history, evidence, and crypto
operations, enabling pluggable implementations for different deployment scenarios.

ADR-033: Provider Interfaces for History/Evidence/Crypto
"""

from .crypto_provider import CryptoProvider, NoCrypto
from .evidence_sink import EvidenceSink, NoneEvidence
from .history_provider import EdgeOnlyHistory, HistoryProvider

__all__ = [
    "CryptoProvider",
    # No-op implementations (v1)
    "EdgeOnlyHistory",
    "EvidenceSink",
    # Interfaces
    "HistoryProvider",
    "NoCrypto",
    "NoneEvidence",
]
