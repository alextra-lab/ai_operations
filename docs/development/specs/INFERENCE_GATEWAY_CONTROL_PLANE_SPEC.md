# Inference Gateway – Control Plane APIs

Status: Draft

Date: 2025-11-02

## Overview

Admin-only APIs to manage providers, aliases, routing policies, and limits.
All endpoints require S2S JWT with `admin` role and `gateway:admin` scope.

## Namespacing

- Base path: `/admin/gateway` (subject to finalization)

## Endpoints (initial)

### Providers

- GET `/admin/gateway/providers`
  - List registered providers and health.

- POST `/admin/gateway/providers`
  - Register provider: `{ name, type, connection: { url, api_key_ref, ... } }`.

- PATCH `/admin/gateway/providers/{name}`
  - Update connection, priority, enable/disable.

### Aliases & Routing

- GET `/admin/gateway/aliases`
  - List aliases with per-tenant overrides.

- PUT `/admin/gateway/aliases/{alias}`
  - Upsert alias policy: `{ targets: [ { provider, model, weight } ], constraints,
    fallback_chain }`.

- PUT `/admin/gateway/aliases/{alias}/tenants/{tenant}`
  - Upsert tenant-specific override policy.

### Limits & Quotas

- GET `/admin/gateway/limits`
  - Current limit configs and effective states.

- PUT `/admin/gateway/limits`
  - Upsert configs: per-tenant/provider/model token-bucket params, bursts,
    quotas (daily tokens/cost).

### Health & Circuit Breakers

- GET `/admin/gateway/health`
  - Provider and target health snapshots.

- POST `/admin/gateway/circuits/{provider}/{model}/open`
  - Manually open/close/half-open for testing and incident control.

## Responses & Errors

- 200/201 on success with JSON body reflecting latest state.
- 400/409 validation/conflict; 403 authorization; 5xx internal.

## Audit & Security

- All writes produce audit events with `who, what, when, before/after`.
- Secret refs only (never raw keys). Keys stored via secrets manager.
