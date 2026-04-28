# ADR-052: Model Aliasing, Routing, and Provider Fallback

Status: Proposed

Date: 2025-11-02

## Context

The platform must support multiple inference providers and models with tenant-
specific needs (cost, latency, capabilities). Today, orchestrator performs
intent-aware selection but provider/model routing and fallback are distributed
or missing. A central policy in the Inference Gateway is required.

## Decision

- Model Aliases
  - Define tenant-scoped logical model aliases (e.g., `alias: soc_default_gpt`)
    that resolve to concrete provider+model (e.g., `openai:gpt-4o-mini`).
  - Aliases include policy metadata: max output tokens, preferred sampling
    presets, capabilities (tools/vision), and cost/latency targets.

- Routing Policy
  - Gateway resolves alias → provider target using:
    1) tenant policy, 2) global default, 3) static fallback.
  - Health and circuit-breaker state influence routing (avoid degraded targets).
  - Per-request overrides can pin a target if authorized (admin/testing).

- Provider Fallback
  - Gateway performs provider-level failover on transient errors/timeouts using
    predefined fallback chains per alias (e.g., `gpt-4o-mini` → `gpt-4o` → local).
  - Fallback respects capability constraints and maximum attempts.

- Orchestrator Interaction
  - Orchestrator continues intent-aware selection (e.g., QUERY vs SUMMARIZE)
    but requests model by alias; Gateway decides provider target and fallback.

## Rationale

Separating intent selection (business) from provider routing (platform) avoids
duplication, reduces conflicts, and consolidates health/cost controls.

## Consequences

- Alias registry and policy store in Gateway control plane.
- Clear error taxonomy for fallback exhaustion and partial failures.

## Policy Elements

- Per-tenant alias map {alias → [targets ordered], constraints, budgets}.
- Health scoring with hysteresis (open/half-open/closed circuits per target).
- Cost and latency budgets (soft constraints to steer selection).

## Acceptance Criteria

- Alias resolution deterministic given health state and policy.
- Provider failover engages on transient errors and respects attempt limits.
- End-to-end metrics attribute usage to original alias and resolved target.

## References

- ADR-050 Inference Gateway and Responsibility Split
- ADR-053 Rate Limiting and Quotas (complements routing decisions)
