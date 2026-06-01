# Architecture Decision Records (ADRs)

**Total ADRs:** 42 (ADR-001 through ADR-072)
**Last Updated:** February 18, 2026
**Latest:** ADR-072 - Remove Deprecated Intent Model and Temperature Environment Configuration

---

## About ADRs

This directory contains Architecture Decision Records for the AI Operations Platform project. ADRs document significant architectural decisions, their context, and consequences.

### Format

Each ADR follows the industry-standard format (Michael Nygard):

- **Title**: Clear description of the decision
- **Status**: PROPOSED | ACCEPTED | DEPRECATED | SUPERSEDED
- **Date**: When the decision was made
- **Context**: Background and problem statement
- **Decision**: What was decided and why
- **Consequences**: Positive, negative, and neutral impacts
- **Alternatives Considered**: Other options and why they weren't chosen

See [`template.md`](template.md) for the complete format.

---

## Complete ADR Index

### Security & Authentication

- **[ADR-037](ADR-037-uuid-primary-keys.md)**: UUID Primary Keys (ACCEPTED)
- **[ADR-039](ADR-039-rls-security-model.md)**: Row-Level Security Model (ACCEPTED)
- **[ADR-048](ADR-048-Secure-Logging-Redaction.md)**: Secure Logging and Redaction (ACCEPTED)
- **[ADR-049](ADR-049-Unified-Authentication-Security-Implementation.md)**: Unified Authentication and Security Implementation (ACCEPTED 2025-11-02)
- **[ADR-056](ADR-056-MCP-Tool-Registration-Workflow.md)**: MCP Tool Registration Workflow (ACCEPTED 2025-11-24)

### Database & Schema

- **[ADR-021](ADR-021-Collection-Based-Document-Management.md)**: Collection-Based Document Management (ACCEPTED)
- **[ADR-022](ADR-022-Backend-Async-Database-Migration.md)**: Backend Async Database Migration (ACCEPTED)
- **[ADR-037](ADR-037-uuid-primary-keys.md)**: UUID Primary Keys (ACCEPTED)
- **[ADR-038](ADR-038-jsonb-for-config.md)**: JSONB for Configuration (ACCEPTED)
- **[ADR-039](ADR-039-rls-security-model.md)**: RLS Security Model (ACCEPTED)
- **[ADR-040](ADR-040-telemetry-vs-transcripts.md)**: Telemetry vs Transcripts (ACCEPTED)
- **[ADR-041](ADR-041-Role-Based-Use-Case-Permissions.md)**: Role-Based Use Case Permissions (ACCEPTED)

### Architecture Patterns

- **[ADR-001](ADR-001-hybrid-tools-architecture.md)**: Hybrid Tools Architecture (ACCEPTED)
- **[ADR-016](ADR-016-Dynamic-Intent-System.md)**: Dynamic Intent System (ACCEPTED)
- **[ADR-018](ADR-018-Use-Case-Owned-Architecture.md)**: Use Case Owned Architecture (ACCEPTED)
- **[ADR-020](ADR-020-Use-Case-Publisher-Role.md)**: Use Case Publisher Role (ACCEPTED)
- **[ADR-023](ADR-023-Sampling-Presets-and-Guardrails.md)**: Sampling Presets and Guardrails (ACCEPTED)
- **[ADR-033](ADR-033-Provider-Interfaces.md)**: Provider Interfaces (ACCEPTED)
- **[ADR-035](ADR-035-Service-Boundary-Clarification.md)**: Service Boundary Clarification (ACCEPTED)
- **[ADR-036](ADR-036-Orchestrator-Pipeline-Pattern.md)**: Orchestrator Pipeline Pattern (ACCEPTED)
- **[ADR-043](ADR-043-Conversations-As-QUERY-Pattern.md)**: Conversations as QUERY Pattern (ACCEPTED)
- **[ADR-044](ADR-044-Use-Cases-As-Bounded-Refinement-Spaces.md)**: Use Cases as Bounded Refinement Spaces (ACCEPTED)

### Frontend & UI

- **[ADR-012](ADR-012-Hybrid-CSS-Strategy.md)**: Hybrid CSS Strategy (Material + Tailwind + SCSS) (ACCEPTED)
- **[ADR-013](ADR-013-Material-Only-Strategy.md)**: Material-Only Strategy (SUPERSEDED by ADR-012)
- **[ADR-014](ADR-014-Tailwind-Only-Strategy.md)**: Tailwind-Only Strategy (SUPERSEDED by ADR-012)
- **[ADR-015](ADR-015-custom-llm-content-renderer.md)**: Custom LLM Content Renderer (ACCEPTED)
- **[ADR-045](ADR-045-Query-Developer-Tools.md)**: Query Developer Tools (ACCEPTED)
- **[ADR-059](ADR-059-Client-Side-Conversation-Session-Management-UX.md)**: Client-Side Conversation Session Management UX (ACCEPTED 2025-12-07)

### Stateless Core (v1)

- **[ADR-030](ADR-030-No-Transcripts-Run-Manifests.md)**: No Transcripts; Run Manifests Only (ACCEPTED)
- **[ADR-031](ADR-031-Client-Owned-Exports.md)**: Client-Owned Exports & Summary Generation (ACCEPTED)
- **[ADR-032](ADR-032-Capabilities-Edition-Flags.md)**: Capabilities & Edition Flags (ACCEPTED)
- **[ADR-033](ADR-033-Provider-Interfaces.md)**: Provider Interfaces for History/Evidence/Crypto (ACCEPTED)
- **[ADR-043](ADR-043-Conversations-As-QUERY-Pattern.md)**: Conversations as QUERY Pattern (ACCEPTED)
- **[ADR-047](ADR-047-Ephemeral-Cache-Observability.md)**: Ephemeral Cache Observability (ACCEPTED)
- **[ADR-059](ADR-059-Client-Side-Conversation-Session-Management-UX.md)**: Client-Side Conversation Session Management UX ⭐ **LATEST** (ACCEPTED 2025-12-07)

### Use Case Management

- **[ADR-017](ADR-017-Prompt-Patterns-and-Blueprints-v1.md)**: Prompt Patterns and Blueprints v1 (ACCEPTED)
- **[ADR-018](ADR-018-Use-Case-Owned-Architecture.md)**: Use Case Owned Architecture (ACCEPTED)
- **[ADR-034](ADR-034-Use-Case-Validation-Harness.md)**: Use Case Validation & Test Harness (ACCEPTED)
- **[ADR-041](ADR-041-Role-Based-Use-Case-Permissions.md)**: Role-Based Use Case Permissions (ACCEPTED)
- **[ADR-044](ADR-044-Use-Cases-As-Bounded-Refinement-Spaces.md)**: Use Cases as Bounded Refinement Spaces (ACCEPTED)

### Pricing & Analytics

- **[ADR-042](ADR-042-Simplified-Category-Pricing.md)**: Simplified Category Pricing (ACCEPTED)
- **[ADR-046](ADR-046-Per-Model-Pricing-With-History.md)**: Per-Model Pricing with History (ACCEPTED)

### Configuration & Environment

- **[ADR-069](ADR-069-Intent-Model-Configuration-System.md)**: Intent Model Configuration System (ACCEPTED 2026-02-08)
- **[ADR-071](ADR-071-Centralized-Configuration-Gateway.md)**: Centralized Configuration Gateway — shared/config (ACCEPTED 2026-02-18)
- **[ADR-072](ADR-072-Remove-Deprecated-Intent-Env-Config.md)**: Remove Deprecated Intent Model/Temperature Env Config (ACCEPTED 2026-02-18)

### Deployment & Operations

- **[ADR-019](ADR-019-Offline-Tokenizer-Strategy.md)**: Offline Tokenizer Strategy (ACCEPTED)
- **[ADR-022](ADR-022-Backend-Async-Database-Migration.md)**: Backend Async Database Migration (ACCEPTED)
- **[ADR-074](ADR-074-multi-profile-build-and-bootstrap.md)**: Multi-Profile Container Build & Reproducible Bootstrap (PROPOSED 2026-05-30) ⭐ **LATEST**

---

## Index by Status

### ✅ ACCEPTED (Active)

All accepted ADRs (40):

- ADR-001, ADR-012, ADR-015, ADR-016, ADR-017, ADR-018, ADR-019, ADR-020
- ADR-021, ADR-022, ADR-023, ADR-030, ADR-031, ADR-032, ADR-033, ADR-034
- ADR-035, ADR-036, ADR-037, ADR-038, ADR-039, ADR-040, ADR-041, ADR-042
- ADR-043, ADR-044, ADR-045, ADR-046, ADR-047, ADR-048, ADR-049, ADR-054
- ADR-060, ADR-065, ADR-067, ADR-068, ADR-069, ADR-070, ADR-071, ADR-072

### ⏸️ SUPERSEDED (Historical)

- **ADR-013**: Material-Only Strategy (superseded by ADR-012)
- **ADR-014**: Tailwind-Only Strategy (superseded by ADR-012)

### 📋 PROPOSED (Pending Review)

- **ADR-074**: Multi-Profile Container Build & Reproducible Bootstrap (2026-05-30)

---

## Recent Additions

### June 2026

**2026-06-01:**

- **ADR-073** updated: LLG-02 (AIO-3) and LLG-03 (AIO-2) shipped (PR #85). D6 reframed from "deferred" to **replacement required** — `llm-guard==0.3.16` is the final release and pins `transformers==4.51.3`, so the open `transformers` CVEs have no upstream fix path. Also recorded that the ai4privacy PII model (and ADR Option A) is `cc-by-nc-4.0` (non-commercial). LLG-04 (AIO-1) promoted to committed; Option B selected (Presidio + GLiNER). See `analysis/llm-guard-replacement-evaluation.md`.

### May 2026

**2026-05-30:**

- **ADR-074**: [Multi-Profile Container Build & Reproducible Bootstrap](ADR-074-multi-profile-build-and-bootstrap.md) ⭐ **LATEST**
  - Three build profiles: local (public registries), enterprise (Artifactory mirrors), train (offline wheelhouse)
  - Corrects prior misclassification: offline wheelhouse = personal convenience, NOT enterprise path
  - Enterprise = GitLab CI + Artifactory; no direct HuggingFace access; internal LLMaaS/vLLM
  - Single parametrized Dockerfile per service (ARGs: BASE_REGISTRY, PIP_INDEX_URL, OFFLINE, NPM_REGISTRY)
  - DB bootstrap wired into compose via one-shot `db-init` service
  - Execution: M1–M4 per `docs/development/plans/BUILD_BOOTSTRAP_PLAN.md`

### February 2026

**2026-02-18:**

- **ADR-072**: [Remove Deprecated Intent Model/Temperature Env Config](ADR-072-Remove-Deprecated-Intent-Env-Config.md) ⭐ **LATEST**
  - Completes ADR-069 cleanup: removes ghost intent fields from shared/config schemas and loader
  - Retires ParameterManager env reads; retains as code-level fallback only
  - Cleans `INTENT_MODEL_*` and `INTENT_TEMP_*` from env files and templates
  - First application of ADR-071 Section 5 (DB supersedes env)

- **ADR-071**: [Centralized Configuration Gateway](ADR-071-Centralized-Configuration-Gateway.md)
  - Formalizes shared/config as the single gateway for all runtime configuration
  - Documents bootstrap exceptions, naming conventions, template governance
  - Catalogs 15+ drift sites requiring cleanup
  - Foundation for ADR-061 (Vault) integration

**2026-02-08:**

- **ADR-069**: [Intent Model Configuration System](ADR-069-Intent-Model-Configuration-System.md)
  - Replaces env-based intent model config with DB-driven defaults
  - Deterministic lookup: use case pin → intent default → error
  - Per-intent temperature via Admin UI
  - Foundation for future agentic model routing

### November 2025

**2025-11-02:**

- **ADR-049**: [Unified Authentication and Security Implementation](ADR-049-Unified-Authentication-Security-Implementation.md)
  - Documents complete authentication architecture (JWT, RBAC, multi-layer security)
  - Security audit findings and compliance assessment
  - Comprehensive implementation details for all microservices
  - Frontend-backend authentication integration
  - Related: ADR-037 (UUIDs), ADR-039 (RLS), ADR-048 (Secure Logging)

### October 2025

**2025-10-26:**

- **ADR-047**: [Ephemeral Cache Observability](ADR-047-Ephemeral-Cache-Observability.md)
  - Metrics and monitoring for ephemeral conversation cache
  - SLIs and SLOs for cache performance
  - Production observability patterns

**2025-10-26:**

- **ADR-044**: [Use Cases as Bounded Refinement Spaces](ADR-044-Use-Cases-As-Bounded-Refinement-Spaces.md)
  - Defines core architectural principle for use case system
  - Explains domain-constrained AI assistants
  - Documents structured vs conversational interaction modes
  - Clarifies multi-turn refinement within boundaries

**2025-10-24:**

- **ADR-041**: [Role-Based Use Case Permissions](ADR-041-Role-Based-Use-Case-Permissions.md)
  - Critical architecture fix for RBAC model
  - Removes incorrect intent-based permissions
  - Implements correct use-case-based permissions
  - Task: P4-TASK-14

**2025-10-23:**

- **ADR-036**: [Orchestrator Pipeline Pattern](ADR-036-Orchestrator-Pipeline-Pattern.md)

**2025-10-22:**

- **ADR-030-035**: Stateless Core v1 ADRs

**2025-10-20:**

- **ADR-023**: [Sampling Presets and Guardrails](ADR-023-Sampling-Presets-and-Guardrails.md)

---

## Key Architectural Themes

### 🔒 Security First

- UUID-based identifiers (ADR-037)
- Row-Level Security at database layer (ADR-039)
- Unified authentication system (ADR-049)
- Secure logging with redaction (ADR-048)

### 📦 Stateless by Design

- Client-side conversation storage (ADR-030)
- Ephemeral encrypted cache (ADR-047)
- Run manifests only (no transcripts) (ADR-030)
- Client-owned exports (ADR-031)

### 🎯 Use Case Driven

- Use cases as sovereign entities (ADR-018)
- Bounded refinement spaces (ADR-044)
- Template-driven patterns (ADR-017)
- Role-based access control (ADR-041)

### 🏗️ Service Architecture

- Hybrid tools architecture (ADR-001)
- Service boundary clarification (ADR-035)
- Orchestrator pipeline pattern (ADR-036)
- Provider interfaces (ADR-033)

---

## Related Documentation

- **[Project Overview](../../PROJECT_OVERVIEW.md)** - High-level project summary
- **[Master Roadmap](../plans/MASTER_ROADMAP.md)** - Implementation timeline
- **[Architecture Docs](../../architecture/)** - System architecture details
- **[Security Audit (2025-11-02)](../analysis/security-audit-2025-11-02.md)** - Latest security assessment

---

## Contributing

### Creating a New ADR

1. **Use the next available number** (ADR-073)
2. **Start with status PROPOSED**
3. **Follow the standard format** (see [`template.md`](template.md))
4. **Link related ADRs and tasks**
5. **Update this README index**
6. **Update PROJECT_OVERVIEW.md** if it's a key architectural decision
7. **Notify the team** for review

### ADR Review Process

1. Create ADR in PROPOSED status
2. Team review and discussion
3. Update status to ACCEPTED once approved
4. Cross-link related ADRs
5. Update architectural documentation

### Superseding an ADR

If an ADR becomes obsolete:

1. Update old ADR status to SUPERSEDED
2. Add reference to new ADR
3. Update this index
4. Keep old ADR for historical reference

---

**Template:** [`template.md`](template.md)
**Latest ADR:** [ADR-072 - Remove Deprecated Intent Model/Temperature Env Config](ADR-072-Remove-Deprecated-Intent-Env-Config.md)
