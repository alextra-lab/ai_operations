# ADR-046: Per-Model Pricing with Effective-Dated History

**Status:** Accepted
**Date:** 2025-10-29
**Deciders:** Architecture Team, AI Assistant
**Tags:** pricing, cost-model, audit, analytics, admin-ui

---

## Context

- ADR-042 introduced a simplified 3-category pricing model (A/B/C) to
  replace a 15-tier matrix. That reduced operational complexity but does
  not provide per-model control or price history.
- Requirements confirmed by product/engineering (Option A):
  1) Each model has configurable input/output cost set in the Model
     Configuration UI; 2) pricing changes must be tracked by effective
     date; 3) pricing must drive backend cost calculation and Token
     Analytics; 4) backward compatibility is not required (pre-release).
- The database initialization script already contains per-model pricing
  support and history tables: `models` supports current prices and
  `model_pricing_history` stores effective-dated records, plus helper
  function `get_active_model_price(model_uuid, as_of)`.

## Decision

Adopt per-model, effective-dated pricing as the source of truth.

- Store prices per model (EUR per 1M tokens) with history windows
  [`effective_from`, optional `effective_to`].
- The active price at execution time is determined by the most recent
  history record where `effective_from <= as_of < effective_to | NULL`.
- Admins manage prices in the Model configuration UI (create new price
  records, optionally scheduled via `effective_from`).
- The pricing calculator (backend) queries the active price for the
  model at request time and returns cost-per-million values to compute
  `cost_per_1k_*` and `total_cost` for `token_usage`.
- Token Analytics uses immutable costs captured at execution time; no
  retroactive recalculation is performed.

## Consequences

Positive:

- Fine-grained control (per-model) with clear auditability over time.
- Clean analytics: “actual cost at execution” is immutable; “what-if
  current pricing” comparisons remain possible in analytics.
- Clear separation of concerns: pricing vs. rate limits (rate limits are
  managed independently per P4-F7).

Tradeoffs:

- Slightly higher UI/UX complexity (price history management).
- Category-tier shortcuts become optional seeds, not the primary model.

## Implementation Notes

Schema (already present in init script):

- `models.input_price_per_million`, `models.output_price_per_million`
- `model_pricing_history` with `(model_id, input_price_per_million,
  output_price_per_million, effective_from, effective_to, changed_by,
  change_reason)` and indexes for point-in-time lookup
- `get_active_model_price(model_uuid, p_as_of TIMESTAMPTZ)` helper

Backend updates:

- Cost estimator uses DB-backed active price lookup by model UUID or
  model identifier -> resolve to UUID -> call `get_active_model_price`.
- Record `cost_per_1k_in`, `cost_per_1k_out`, `total_cost` in
  `token_usage` at write-time; do not recalc later.
- Admin endpoints to create price changes and list history.
  See: [Admin Pricing API](../../api/admin_pricing.md)
- **Note (2025-12-10)**: `ResponseFormatter.process()` and `_consolidate_metrics()`
  are async to properly await `estimate_cost()`. Cost estimation must be awaited
  in async context; cannot use `asyncio.run()` from running event loop.

Frontend updates:

- Model Configuration → new Pricing tab:
  - Shows current active price and currency (EUR per 1M tokens)
  - "Change Price" dialog (input/output costs, effective_from, reason)
  - Price history table (descending by effective_from)
- Token Analytics uses recorded immutable costs; may add “current price
  vs actual” deltas in a future enhancement.

Testing:

- Unit: effective price selection across boundaries, rounding, fallbacks
- Integration: orchestration → token tracker writes expected costs
- UI: price change flow, validations, history table display

## Migration & Rollout

- No backward compatibility required (pre-release). Existing data can be
  left as-is; seed an initial history row per model if missing. Category
  tiers (ADR-042) may be kept only as optional seed/defaults.

## Status

- Accepted on 2025-10-29. Supersedes ADR-042 as the primary pricing
  model. ADR-042 remains as a reference for category-based defaults.

## References

- ADR-042: Simplified Category-Based Pricing Model (superseded)
- Database init script sections:
  - Models, Model Pricing History, helper function
  - Token Usage for immutable cost capture
- API: [Admin Pricing API](../../api/admin_pricing.md)
