# ADR-033: Provider Interfaces for History/Evidence/Crypto

**Status:** Accepted
**Date:** 2025-10-22
**Deciders:** Architecture Team
**Tags:** providers, interfaces, stateless, future-proof

---

## Context

**What is the issue we're addressing?**

The stateless architecture (ADR-030) eliminates server-side conversation storage, but we need:

- **Future-Proof Architecture:** Clean interfaces for optional stateful capabilities (v2+)
- **Provider Abstraction:** Pluggable providers for history, evidence, and crypto operations
- **No-Op Implementation:** Stateless v1 needs no-op providers that don't store data
- **Clean Seams:** Easy transition to stateful providers without architectural changes

**Current limitations:**
- Hardcoded assumptions about data storage throughout codebase
- No abstraction for history, evidence, or crypto operations
- Difficult to add stateful capabilities without major refactoring
- Missing interfaces for future governed providers

**Forces at play:**
- Stateless v1 requirements (no server-side storage)
- Future stateful v2+ requirements (governed providers)
- Need for clean architecture without breaking changes
- Enterprise requirements for pluggable security providers

---

## Decision

**What did we decide?**

**Implement provider interfaces with no-op implementations for v1:**

- **Provider Interfaces:** Abstract interfaces for HistoryProvider, EvidenceSink, CryptoProvider
- **No-Op Implementations:** Stateless providers that don't store data (v1)
- **Factory Pattern:** Runtime provider selection based on configuration
- **Future-Ready:** Clean interfaces for governed providers (v2+)
- **Pluggable Architecture:** Easy to swap providers without code changes

**Key Implementation Details:**
- HistoryProvider: append() and fetch() methods (no-op for v1)
- EvidenceSink: store() and retrieve() methods (no-op for v1)
- CryptoProvider: encrypt() and decrypt() methods (no-op for v1)
- Provider factory selects implementation based on environment variables
- All providers implement same interfaces regardless of actual functionality

---

## Alternatives Considered

### Option 1: No Provider Abstraction
**Description:** Hardcode no-op behavior throughout codebase
**Pros:**
- Simple implementation
- No abstraction overhead

**Cons:**
- Difficult to add stateful capabilities later
- Code changes required for provider switching
- No clean architecture for future features
- Violates open/closed principle

**Why Rejected:** Creates technical debt and blocks future stateful capabilities

### Option 2: Full Provider Implementation
**Description:** Implement full providers even for stateless v1
**Pros:**
- Complete functionality from start
- No future migration needed

**Cons:**
- Violates stateless architecture principles
- Adds security scope and complexity
- Overkill for v1 requirements
- Conflicts with air-gapped deployment goals

**Why Rejected:** Conflicts with stateless architecture and security requirements

### Option 3: Conditional Provider Logic
**Description:** Use if/else logic to choose provider behavior
**Pros:**
- Simple conditional logic
- No interface overhead

**Cons:**
- Scattered conditional logic throughout codebase
- Difficult to test different provider combinations
- No clean separation of concerns
- Hard to maintain and extend

**Why Rejected:** Creates maintenance burden and testing complexity

---

## Consequences

### Positive Consequences

**Benefits of this decision:**
- **Clean Architecture:** Clear separation between stateless and stateful concerns
- **Future-Proof:** Easy to add governed providers without architectural changes
- **Testable:** Easy to mock providers for testing
- **Pluggable:** Runtime provider selection without code changes
- **Stateless Compliant:** No-op providers maintain stateless architecture
- **Enterprise Ready:** Foundation for governed provider integration

### Negative Consequences

**Tradeoffs and costs:**
- **Interface Overhead:** Additional abstraction layer
- **Implementation Complexity:** Must implement no-op providers
- **Documentation Burden:** Must document all provider interfaces
- **Testing Matrix:** More provider combinations to test

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Interface changes | Medium | Version interfaces, maintain backward compatibility |
| Provider confusion | Low | Clear documentation, comprehensive examples |
| Performance overhead | Low | No-op providers have minimal overhead |

---

## Implementation Notes

**Key implementation details:**

**Provider Interfaces:**
```python
from typing import Any, List, Optional, Protocol
from uuid import UUID

class HistoryProvider(Protocol):
    """Protocol for history persistence."""

    async def append(self, run_id: UUID, payload: dict[str, Any]) -> None:
        """Append history entry."""
        ...

    async def fetch(
        self,
        case_id: Optional[str] = None,
        run_id: Optional[UUID] = None
    ) -> List[dict[str, Any]]:
        """Fetch history entries."""
        ...

class EvidenceSink(Protocol):
    """Protocol for evidence storage."""

    async def store(self, evidence: dict[str, Any]) -> str:
        """Store evidence, return ID."""
        ...

    async def retrieve(self, evidence_id: str) -> dict[str, Any]:
        """Retrieve evidence by ID."""
        ...

class CryptoProvider(Protocol):
    """Protocol for cryptographic operations."""

    async def encrypt(self, data: str) -> str:
        """Encrypt data."""
        ...

    async def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data."""
        ...
```

**No-Op Implementations:**
```python
class EdgeOnlyHistory:
    """No-op history provider for stateless v1."""

    async def append(self, run_id: UUID, payload: dict[str, Any]) -> None:
        """No-op: history lives on client edge."""
        pass

    async def fetch(self, case_id: Optional[str] = None, run_id: Optional[UUID] = None) -> List[dict[str, Any]]:
        """No-op: return empty list."""
        return []

class NoneEvidence:
    """No-op evidence sink for stateless v1."""

    async def store(self, evidence: dict[str, Any]) -> str:
        """No-op: return dummy ID."""
        return "none"

    async def retrieve(self, evidence_id: str) -> dict[str, Any]:
        """No-op: return empty dict."""
        return {}

class NoCrypto:
    """No-op crypto provider for stateless v1."""

    async def encrypt(self, data: str) -> str:
        """No-op: return data as-is."""
        return data

    async def decrypt(self, encrypted_data: str) -> str:
        """No-op: return data as-is."""
        return encrypted_data
```

**Provider Factory:**
```python
def create_providers() -> tuple[HistoryProvider, EvidenceSink, CryptoProvider]:
    """Create providers based on configuration."""
    history_provider = EdgeOnlyHistory() if HISTORY_PROVIDER == "none" else GovernedHistory()
    evidence_sink = NoneEvidence() if EVIDENCE_SINK == "none" else WormEvidence()
    crypto_provider = NoCrypto() if CRYPTO_PROVIDER == "none" else KmsCrypto()

    return history_provider, evidence_sink, crypto_provider
```

**Files affected:**
- `src/orchestrator/app/services/providers/` (new directory)
- `src/orchestrator/app/services/providers/edge_only_history.py`
- `src/orchestrator/app/services/providers/none_evidence.py`
- `src/orchestrator/app/services/providers/no_crypto.py`
- `src/orchestrator/app/services/providers/__init__.py`
- `src/orchestrator/app/schemas/provider_interfaces.py`

**Future Governed Providers (v2+):**
- GovernedHistory: Full history persistence with audit trails
- WormEvidence: Write-once-read-many evidence storage
- KmsCrypto: Enterprise key management integration

---

## References

- [ADR-030: No Transcripts; Run Manifests Only](ADR-030-No-Transcripts-Run-Manifests.md)
- [ADR-032: Capabilities & Edition Flags](ADR-032-Capabilities-Edition-Flags.md)
- [Stateless Core v1 Implementation Plan](../plans/STATELESS_CORE_V1_IMPLEMENTATION_PLAN.md)

---

## Status Updates

### 2025-10-22 - Accepted
**Changed By:** Architecture Team
**Reason:** Essential for future-proof architecture and clean stateless implementation

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
