# ADR-053: Rate Limiting and Quotas per Tenant/Provider/Model

Status: Proposed

Date: 2025-11-02

## Context

The platform serves multiple tenants and services with varying budgets and
throughput. We must prevent abuse, ensure fairness, protect providers from
overload, and meet cost controls. Limits must apply across chat and embeddings.

## Decision

- Define hierarchical limits and quotas enforced in the Inference Gateway:
  - Per-tenant global (requests/sec, tokens/sec, daily tokens/cost)
  - Per-tenant per-provider
  - Per-tenant per-model (resolved target)

- Algorithms
  - Rate limits: token-bucket (leaky-bucket equivalent acceptable) with burst
    capacity; Redis-compatible counter for distributed enforcement.
  - Quotas: rolling daily windows for tokens and cost; monthly optional.

- Rejection Semantics
  - 429 Too Many Requests for rate excess with `Retry-After`.
  - 402 Payment Required (or 403) for quota exhaustion with structured error
    details (`limit_type`, `window_end`, `suggested_action`).

- Telemetry
  - Emit counters and gauges per tenant/provider/model for limits and quota
    states; include request_id for correlation.

## Rationale

Centralized enforcement guarantees consistent behavior across services and
providers, enabling predictable cost and SLOs.

## Consequences

- Gateway requires fast, resilient store (e.g., Redis) for distributed tokens.
- Callers must handle 429/402 gracefully and optionally back off.

## Acceptance Criteria

- Limits enforced accurately under concurrency with <5% error at p99.
- Backoff headers present on 429; descriptive payload on quota errors.
- Dashboards for limit utilization and quota burn-down by tenant.

## References

- ADR-050 Inference Gateway and Responsibility Split
- ADR-051 Provider Secrets and S2S Auth
