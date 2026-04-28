# ADR-032: Capabilities & Edition Flags

**Status:** Accepted
**Date:** 2025-10-22
**Deciders:** Architecture Team
**Tags:** capabilities, feature-flags, editions, configuration

---

## Context

**What is the issue we're addressing?**

The stateless architecture requires clear capability boundaries and feature flags to:

- **Edition Management:** Distinguish between Core (stateless) and Plus (future stateful) editions
- **Feature Gating:** Enable/disable features based on deployment configuration
- **Provider Selection:** Choose appropriate providers (none vs. governed) for different environments
- **Runtime Configuration:** Allow dynamic capability discovery without hardcoded assumptions

**Current limitations:**
- No clear distinction between stateless and stateful capabilities
- Hardcoded feature assumptions throughout the codebase
- No runtime capability discovery mechanism
- Missing configuration for air-gapped vs. connected deployments

**Forces at play:**
- Stateless v1 vs. future stateful v2+ capabilities
- Air-gapped deployment requirements
- Enterprise vs. development environment differences
- Need for clean capability boundaries

---

## Decision

**What did we decide?**

**Implement capabilities system with edition flags and feature toggles:**

- **Edition Flags:** Core (stateless) vs. Plus (future stateful) editions
- **Provider Flags:** None (v1) vs. Governed (v2+) provider configurations
- **Feature Flags:** Enable/disable specific capabilities at runtime
- **Capabilities Endpoint:** Runtime discovery of available features
- **Configuration-Driven:** All capabilities controlled via environment variables

**Key Implementation Details:**
- Edition determines base capability set (Core = stateless, Plus = stateful)
- Provider flags control history/evidence/crypto provider selection
- Feature flags enable optional capabilities (expert chunking, advanced analytics)
- Capabilities endpoint returns current configuration and available features
- Environment variables control all capability decisions

---

## Alternatives Considered

### Option 1: Hardcoded Capabilities
**Description:** Build capabilities into code with compile-time decisions
**Pros:**
- Simple implementation
- No runtime overhead

**Cons:**
- Inflexible deployment options
- Difficult to support multiple editions
- No runtime capability discovery
- Hard to test different configurations

**Why Rejected:** Too inflexible for enterprise deployment requirements

### Option 2: Database-Driven Capabilities
**Description:** Store capability configuration in database
**Pros:**
- Dynamic capability changes
- Centralized configuration

**Cons:**
- Database dependency for basic functionality
- Complex migration scenarios
- Security concerns for capability configuration
- Overkill for static capability sets

**Why Rejected:** Overly complex for relatively static capability sets

### Option 3: File-Based Configuration
**Description:** Store capabilities in configuration files
**Pros:**
- Version-controlled configuration
- Environment-specific settings

**Cons:**
- Requires application restart for changes
- File management complexity
- Less flexible than environment variables

**Why Rejected:** Environment variables provide better deployment flexibility

---

## Consequences

### Positive Consequences

**Benefits of this decision:**
- **Flexible Deployment:** Support air-gapped, connected, and hybrid deployments
- **Edition Clarity:** Clear distinction between Core and Plus capabilities
- **Runtime Discovery:** Clients can discover available capabilities
- **Testing Support:** Easy to test different capability combinations
- **Future-Proof:** Clean path to add stateful capabilities (v2+)
- **Configuration-Driven:** All capabilities controlled via environment

### Negative Consequences

**Tradeoffs and costs:**
- **Configuration Complexity:** More environment variables to manage
- **Runtime Overhead:** Capabilities endpoint adds minimal latency
- **Documentation Burden:** Must document all capability combinations
- **Testing Matrix:** More combinations to test

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Configuration errors | Medium | Clear documentation, validation, defaults |
| Capability confusion | Low | Clear naming, comprehensive endpoint documentation |
| Performance impact | Low | Capabilities endpoint cached, minimal overhead |

---

## Implementation Notes

**Key implementation details:**

**Environment Variables:**
```bash
# Edition Configuration
EDITION=core                    # core|plus
STATEFUL_ENABLED=false          # true|false

# Provider Configuration
HISTORY_PROVIDER=none           # none|governed
EVIDENCE_SINK=none              # none|worm
CRYPTO_PROVIDER=none            # none|kms

# Feature Flags
ENABLE_EXPERT_CHUNKING=false    # true|false
ENABLE_ADVANCED_ANALYTICS=false # true|false
RUN_MANIFEST_ENABLED=true       # true|false
RUN_MANIFEST_FAIL_OPEN=true     # true|false
```

**Capabilities Endpoint Response:**
```json
{
  "edition": "core",
  "stateful_enabled": false,
  "providers": {
    "history": "none",
    "evidence": "none",
    "crypto": "none"
  },
  "features": {
    "expert_chunking": false,
    "advanced_analytics": false,
    "run_manifests": true,
    "exports": true,
    "summaries": true
  },
  "capabilities": {
    "conversation_storage": false,
    "cross_user_analytics": false,
    "encrypted_storage": false,
    "audit_trails": false,
    "telemetry_only": true
  }
}
```

**Files affected:**
- `config/env/env.template`
- `src/orchestrator/app/schemas/capabilities.py`
- `src/orchestrator/app/services/capabilities_service.py`
- `src/orchestrator/app/routers/capabilities.py`
- `src/frontend-angular/src/app/services/capabilities.service.ts`

**Edition Definitions:**
- **Core Edition:** Stateless, telemetry-only, client-owned exports
- **Plus Edition:** Stateful, governed providers, audit trails, encrypted storage

**Provider Types:**
- **None:** No-op providers for stateless operation
- **Governed:** Full providers for stateful operation (v2+)

---

## References

- [ADR-030: No Transcripts; Run Manifests Only](ADR-030-No-Transcripts-Run-Manifests.md)
- [ADR-033: Provider Interfaces for History/Evidence/Crypto](ADR-033-Provider-Interfaces.md)
- [Stateless Core v1 Implementation Plan](../plans/STATELESS_CORE_V1_IMPLEMENTATION_PLAN.md)

---

## Status Updates

### 2025-10-22 - Accepted
**Changed By:** Architecture Team
**Reason:** Essential for flexible deployment and future stateful capabilities

---

**Template Version:** 1.0
**Based On:** [Michael Nygard's ADR pattern](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
