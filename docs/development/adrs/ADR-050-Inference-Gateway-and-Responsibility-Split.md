# ADR-050: Inference Gateway and Responsibility Split

**Status:** Approved (Updated 2025-11-08)
**Date:** 2025-11-02
**Updated:** 2025-11-08 (Model schema clarification)
**Deciders:** Security Team, Backend Team, Architecture Team
**Tags:** architecture, infrastructure, llm, embeddings, microservices

---

## Update (2025-11-08): Provider Architecture Clarification

**Model Schema:**

- `models.provider_type` (enum) = Provider API type (openai, azure, mistral, anthropic, local)
- `models.provider` (varchar) = Gateway provider instance name (LMStudio, Ollama, NULL)
- Local models (`provider=NULL`) handled by Embedding Service, NOT routed through Gateway

**Provider Types:**

- `openai` = OpenAI-compatible API (LMStudio, Ollama, vLLM, actual OpenAI)
- `azure` = Azure OpenAI (different auth pattern)
- `mistral` = Mistral AI
- `anthropic` = Anthropic Claude
- `local` = Python in-process models (SentenceTransformer), no HTTP API

**Example:**

```python
# Gateway Provider Instance
gateway_providers: {name: "LMStudio", provider_type: "openai", base_url: "http://..."}

# Models using that provider
models: {model_id: "mistral-7b-instruct", provider_type: "openai", provider: "LMStudio"}
models: {model_id: "all-MiniLM-L6-v2", provider_type: "local", provider: NULL}
```

---

## Context

AI Operations Platform integrates multiple AI capabilities (LLMs, embeddings, rerankers) across microservices (orchestrator-api, corpus-service, embedding-service, llm-guard-svc). The application is designed for **department-scale deployment** (10-100 concurrent users in SOC environments) with flexibility to scale from powerful laptops (MacBook Pro M4 Max) to on-premises servers to cloud infrastructure.

### Current Architecture Challenges

**Provider Access Duplication:**

- Orchestrator calls OpenAI directly via `LLMClient` (`src/orchestrator/app/orchestrator/llm_client.py`)
- Embedding Service calls providers via `OpenAIProvider` (`src/embedding/app/providers/openai.py`)
- Each service implements its own retry logic, timeout handling, and error mapping
- Provider API keys spread across multiple services (secret sprawl)

**Missing Cross-Cutting Concerns:**

- No centralized rate limiting (identified as HIGH PRIORITY in security audit 2025-11-02)
- No global usage tracking across services
- No provider health monitoring or circuit breaking
- Inconsistent error handling and user feedback
- Difficult to add new providers (code changes in multiple places)

**Future Requirements:**

- MCP tools integration (Tools Track T1-T4) will need LLM access
- SOAR integrations calling APIs programmatically
- Potential for runaway scripts or misconfigured automations
- Need to enforce upstream provider rate limits (OpenAI: 500 req/min, Mistral: 200 req/min)

### Existing Infrastructure (Leverage, Don't Rebuild)

**Available in `src/shared/`:**

- ✅ **Authentication:** `shared.auth` (JWT, RBAC, TokenPayload)
- ✅ **Logging:** `shared.logging_utils.fastapi` (structured JSON logs)
- ✅ **Database:** `shared.database` (PostgreSQL connection pooling)
- ✅ **Models:** Shared Pydantic schemas and SQLAlchemy models

**Database Assets:**

- ✅ **`models` table:** Model registry with pricing, capabilities, context windows
- ✅ **`model_pricing_history` table:** Temporal pricing with effective windows
- ✅ **`pricing_tiers` table:** LLMaaS tier configurations with rate limits
- ✅ **`run_manifests` table:** Execution telemetry (can be extended for Gateway metrics)

### Related Decisions

- **ADR-036:** Orchestrator Pipeline Pattern (business logic in orchestrator, infrastructure separate)
- **ADR-021:** Collection-Based Document Management (embedding model strategy)
- **ADR-030:** No Transcripts; Run Manifests Only (stateless architecture)
- **ADR-043/044/045:** Ephemeral cache, observability, secure logging
- **ADR-049:** Unified Authentication & Security (S2S JWT, RBAC, audit logging)

---

## Decision

Introduce an **Inference Gateway** microservice that centralizes provider access and cross-cutting concerns while maintaining clear separation of responsibilities.

### Architecture Pattern: Dumb Pipe with Smart Router Extensibility

**Version 1 (MVP):** Simple routing (provider lookup table)
**Version 2 (Future):** Intent-aware routing (cost optimization, load balancing)

Implementation uses **Strategy Pattern** for future extensibility without breaking changes.

### OpenAI-Compatible API Surface

**Public Data Plane Endpoints:**

- `POST /v1/chat/completions` - Chat completions (sync + SSE streaming)
- `POST /v1/embeddings` - Generate embeddings (delegated architecture)
- `GET /v1/models` - List available models

**Internal Control Plane (Admin-only):**

- `POST /admin/gateway/providers` - Register/configure providers
- `PUT /admin/gateway/providers/{name}` - Update provider settings
- `GET /admin/gateway/health` - Provider health status
- `POST /admin/gateway/reload` - Reload configuration (no restart)
- `GET /admin/gateway/metrics` - Usage metrics and limits

### Responsibility Split (ADR-036 Alignment)

| Concern | Owner | Rationale |
|---------|-------|-----------|
| **Business Logic** | Orchestrator | Intent-aware model selection, sampling preset resolution, prompt assembly, RAG orchestration, primary LLM-Guard validation |
| **Infrastructure** | Gateway | Provider routing, retry/timeout, rate limiting, usage metering, cost calculation, error normalization, circuit breaking |
| **Embeddings** | Embedding Service | Local model management (all-MiniLM-L6-v2), delegates remote providers to Gateway |
| **Authentication** | Shared Auth Module | S2S JWT validation (existing `shared.auth`) |
| **Logging** | Shared Logging | Structured logs with redaction (existing `shared.logging_utils`) |

### Integration with Existing Services

**Orchestrator → Gateway:**

```python
# Orchestrator (business logic)
model = self.select_model_for_intent(intent="QUERY")  # Returns "gpt-4o-mini"
preset = use_case.sampling_preset  # "BALANCED"
params = get_effective_params(preset)  # {temperature: 0.65, ...}

# Call Gateway (infrastructure)
response = gateway_client.chat_completion(
    model=model,  # Concrete model ID (no aliases)
    messages=messages,
    temperature=params.temperature,
    max_tokens=params.max_tokens,
    stream=True
)
```

**Embedding Service → Gateway:**

```python
# Embedding Service (manages routing)
if provider_type == "LOCAL":
    # Use local SentenceTransformers
    embeddings = self.local_provider.embed(texts)
else:
    # Delegate to Gateway for remote providers
    embeddings = gateway_client.create_embeddings(
        model=model,  # "text-embedding-3-large"
        input=texts
    )
```

### Embedding Model Architecture (ADR-021 Compliance)

**Critical Design Constraint:** Collections use **concrete model IDs** (immutable), **NOT aliases**.

**Why No Aliases for Embeddings:**

- Different embedding models produce incomparable vector spaces
- Changing model = must re-embed entire collection (expensive)
- Aliases for chat models OK (same task, different quality/cost)
- Aliases for embedding models = data corruption risk

**Collection Schema (Preserved):**

```python
class Collection:
    embedding_model: str  # "text-embedding-3-small" (CONCRETE, immutable)
    embedding_dimensions: int  # 1536
    qdrant_collection_name: str
    # NO alias field
```

### Vision and Tool Support (Forward Compatible)

**Vision Models:**

- Gateway proxies vision messages transparently (no special handling)
- OpenAI format: `{"type": "image_url", "image_url": {"url": "data:..."}}`
- Activated when document image upload feature is ready
- Zero Gateway code changes needed

**Tool/Function Calling:**

- Gateway proxies `tools` array to provider (OpenAI format)
- Provider returns `tool_calls` in response
- **Orchestrator executes tools** (via MCP/Tools Track)
- Gateway is transparent proxy only (no tool execution)

### Security Model (ADR-049 Integration)

**Service-to-Service Authentication:**

- Reuse existing `shared.auth.UnifiedAuthManager`
- Extend `TokenPayload` with optional `scopes` field
- Gateway validates JWT and enforces scopes

**Extended TokenPayload:**

```python
class TokenPayload(BaseModel):
    sub: str          # username or service-id
    user_id: str      # UUID
    role: str         # Single role (admin, service, user, etc.)
    scopes: list[str] = []  # NEW: ["inference:chat", "inference:embed", "gateway:admin"]
    exp: int
    iat: int
    iss: str
    token_type: str
```

**Scope-Based Authorization:**

- Data plane: Requires `inference:chat` or `inference:embed` scope
- Control plane: Requires `gateway:admin` scope + `admin` role

**Secret Management:**

- Provider API keys stored in `gateway_providers` table (encrypted at rest)
- Manual updates via Admin UI or API endpoint
- Simple reload endpoint (no complex hot-reload/rotation)
- Secrets never logged, never in error messages

---

## Rationale

### Why Gateway Pattern?

1. **Eliminates Duplication:** Single implementation of retry, timeout, error mapping, rate limiting
2. **Centralized Control:** One place to manage providers, limits, monitoring
3. **Service Reusability:** Orchestrator, agents, tools, SOAR all use same infrastructure
4. **Security:** Provider keys isolated in one service (reduced attack surface)
5. **Observability:** Unified usage tracking, cost accounting, performance metrics
6. **Future-Proof:** Easy to add providers, routing strategies, caching without changing callers

### Why Dumb Pipe (v1)?

1. **Simplicity:** ~1,000 lines of code vs ~5,000 for smart router
2. **Performance:** Direct routing, minimal latency (<5ms overhead)
3. **Testability:** Simple logic, easy to reason about
4. **Orchestrator Expertise:** Business logic already excellent at model selection
5. **Extensibility:** Strategy Pattern allows v2 upgrade without breaking changes

### Why Not Keep Current Architecture?

| Current Problem | Gateway Solution |
|----------------|------------------|
| Retry logic duplicated in 2+ services | Single retry implementation |
| No rate limiting (security risk) | Centralized rate limiting (Redis-backed) |
| Provider errors inconsistent | Normalized error taxonomy |
| Can't track usage across services | Unified usage logging |
| Adding provider = changes everywhere | Add provider config, no code changes |
| Secret sprawl (orchestrator + embedding) | Secrets in one place |

---

## Consequences

### Positive

✅ **Security:** Rate limiting prevents abuse, secrets centralized, audit trail complete
✅ **Reliability:** Circuit breakers prevent cascading failures, retry logic consistent
✅ **Observability:** Unified metrics (tokens, cost, latency) per user/provider/model
✅ **Maintainability:** Provider logic in one place, easier debugging
✅ **Scalability:** Gateway can scale horizontally (Redis-backed state)
✅ **Compliance:** Usage tracking for cost analysis, noisy neighbor detection

### Negative

❌ **Added Latency:** One network hop (~2-5ms in Docker internal network)
❌ **New Dependency:** Redis for circuit breaker state and rate limiting
❌ **Migration Effort:** 1-2 weeks to migrate orchestrator/embedding service
❌ **New HA Surface:** Gateway must be highly available (mitigated by horizontal scaling)

### Mitigation Strategies

**Latency:**

- HTTP/2 keep-alive connections to providers
- Connection pooling (reuse connections)
- Co-locate Gateway with orchestrator (same Docker network)
- Streaming passthrough (no buffering)
- Target: p95 added latency <10ms

**Reliability:**

- Multiple Gateway instances (Docker Swarm or Kubernetes)
- Health checks and readiness probes
- Rollback by redeploying a pre-Gateway orchestrator build if necessary

**Redis Dependency:**

- Standalone Redis (v1) - simple, sufficient for department scale
- Fallback to PostgreSQL for rate limiting (slower but works)
- In-memory fallback for development (no persistence)

---

## Scope

### In Scope (v1)

✅ OpenAI-compatible endpoints (`/v1/chat/completions`, `/v1/embeddings`, `/v1/models`)
✅ Provider adapters (OpenAI, LMStudio, VLLM, Mistral)
✅ Rate limiting (global, per-provider, per-integration)
✅ Light circuit breaker (3 failures → open 60s)
✅ Simple retry (2 attempts, exponential backoff)
✅ Usage tracking (PostgreSQL logging)
✅ Cost calculation (read from `models` table)
✅ Streaming passthrough (SSE)
✅ Vision message proxy (ready, inactive until image upload feature)
✅ Tool definition proxy (Gateway passes through, orchestrator executes)
✅ Manual secret management (API/UI update + reload)
✅ Admin UI (provider management, metrics dashboard)

### Out of Scope (v1)

❌ Model aliases (use concrete model IDs only)
❌ Smart routing (intent-aware, cost optimization) - deferred to v2
❌ Response caching (semantic cache) - premature optimization
❌ Secondary LLM-Guard (orchestrator guard is sufficient per ADR-049)
❌ Reranker support (separate endpoint, different use case) - deferred to Phase 5+
❌ Batch processing (`/v1/batches`) - deferred to Phase 5+
❌ Multi-tenant isolation (single organization deployment)
❌ Advanced secret rotation (hot-reload, versioning) - manual is sufficient

### Future Enhancements (v2+)

📋 **Smart Router (Phase 5):** Intent-aware routing, cost optimization, load balancing
📋 **Semantic Cache (Phase 6):** Cache similar prompts, reduce costs
📋 **Advanced Metrics (Phase 6):** Prometheus integration, Grafana dashboards
📋 **Reranker Endpoint (Phase 6):** `/v1/rerank` for corpus management
📋 **Multi-Tenant (Phase 7):** Tenant isolation, per-tenant quotas

---

## Compatibility & Migration

### Backward Compatibility

**Orchestrator Migration (Zero Code Changes):**

```python
# Before (direct OpenAI)
LLMAAS_BASE_URL=https://api.openai.com/v1

# After (via Gateway)
INFERENCE_GATEWAY_URL=http://inference-gateway:8002
```

**Embedding Service Migration (Minimal Changes):**

```python
# Before (direct OpenAI)
openai_client.embeddings.create(...)

# After (via Gateway for remote, local unchanged)
if provider == "local":
    local_provider.embed(...)  # No change
else:
    gateway_client.create_embeddings(...)  # New client
```

### Feature Flags

```python
# Environment configuration
INFERENCE_GATEWAY_URL = os.getenv("INFERENCE_GATEWAY_URL", "http://inference-gateway:8002")

# Orchestrator routing (Gateway only)
client = GatewayClient(base_url=INFERENCE_GATEWAY_URL)
```

### Rollback Strategy

**Gradual Rollout (Completed):**

1. ✅ Deploy Gateway (week 4) - COMPLETE
2. ✅ Test standalone (curl tests, load tests) - COMPLETE
3. ✅ Ship Gateway-enabled orchestrator - COMPLETE (migrated directly to 100%)
4. ✅ Monitor for stability (latency, errors, cost) - COMPLETE
5. ✅ Full cutover to 100% Gateway traffic - COMPLETE
6. ✅ Legacy direct provider access removed - COMPLETE

**Status:** Migration successfully completed. All traffic routes through Gateway.

---

## Department Scale Considerations

**Target Deployment:**

- 10-100 concurrent users (SOC analysts + SOAR integrations)
- 100-500 requests/minute peak load
- Deployable on: Laptop (demo) → On-prem servers → Cloud (future)

**Resource Requirements:**

- Gateway container: 2 CPU, 4GB RAM
- Redis container: 1 CPU, 512MB RAM (50MB actual usage)
- Total overhead: ~500MB memory, minimal CPU

**Scaling Path:**

- Single instance: Handles 500 req/min (sufficient for v1)
- Horizontal scaling: Add instances behind load balancer (future)
- Redis Sentinel: High availability (future, not needed for department scale)

---

## Security Considerations (ADR-049 Compliance)

### Authentication & Authorization

- All requests require valid S2S JWT (validated via `shared.auth`)
- Data plane requires `inference:chat` or `inference:embed` scope
- Control plane requires `gateway:admin` scope + `admin` role
- Request context propagated via `X-Request-ID` header (existing pattern)

### Secret Protection

- Provider API keys stored in `gateway_providers` table (PostgreSQL encrypted at rest)
- Keys loaded on startup, cached in-memory
- Reload endpoint (`POST /admin/gateway/reload`) refreshes without restart
- Keys never logged (ADR-045 redaction rules apply)
- Keys never in error messages (sanitized error responses)

### Audit Trail

- All Gateway requests logged with: `user_id`, `request_id`, `provider`, `model`, `tokens`, `cost`
- Rate limit rejections logged with reason and suggested action
- Provider failures logged with error classification
- Admin actions (provider updates, limit changes) logged in `audit_logs` table

### Logging & Redaction

- Reuse `shared.logging_utils.fastapi` (existing JSON structured logging)
- Prompts/responses redacted by default (ADR-045 compliance)
- Optional sampling for debugging (RBAC-gated, audit trail)
- Cost/token metadata always logged (no PII)

---

## Acceptance Criteria

### Functional

✅ OpenAI SDK compatibility tests pass (sync + streaming)
✅ Vision message proxy works (when tested with image upload)
✅ Tool definition proxy works (verified with mock tool calls)
✅ Rate limiting blocks at configured thresholds
✅ Circuit breaker opens after 3 failures, auto-recovers after 60s
✅ Usage tracking logs all requests with complete metadata
✅ Cost calculation matches orchestrator within 1% variance

### Performance

✅ p95 added latency <10ms vs direct provider (measured at 100 req/min)
✅ Streaming first-byte latency <200ms added overhead
✅ Gateway handles 500 req/min sustained load
✅ Redis operations <1ms (rate limit checks)

### Security

✅ All requests rejected without valid S2S JWT
✅ No provider keys present in logs or error responses
✅ Scope enforcement blocks unauthorized endpoints
✅ Audit trail complete (who, what, when, how much)

### Operational

✅ Gateway starts healthy in <10 seconds
✅ Provider config reload works without restart
✅ Admin UI allows provider management
✅ Metrics dashboard shows usage by user/provider/model
✅ Rollback to direct provider takes <60 seconds

---

## Alternatives Considered

### Alternative 1: Shared Library Only

**Approach:** Create `shared.inference_client` library used by all services

**Pros:**

- Lower effort (~1 week vs 4 weeks)
- No new container
- No network hop

**Cons:**

- ❌ No centralized rate limiting (each service enforces independently)
- ❌ No global usage tracking (fragmented metrics)
- ❌ Circuit breaker state not shared (service A doesn't know service B's provider is down)
- ❌ Secret sprawl continues (keys in multiple services)
- ❌ Duplicate configuration (provider settings copied everywhere)

**Decision:** Rejected - doesn't solve core problems (rate limiting, global state)

### Alternative 2: Keep Orchestrator as Only LLM Client

**Approach:** All LLM access goes through orchestrator (embedding service calls orchestrator)

**Pros:**

- No new service
- Orchestrator already has LLM logic

**Cons:**

- ❌ Tight coupling (embedding service depends on orchestrator)
- ❌ Orchestrator becomes bottleneck (all LLM traffic funneled through one service)
- ❌ MCP tools can't call LLM directly (must go through orchestrator)
- ❌ SOAR integrations tied to orchestrator business logic
- ❌ Violates microservice isolation principles

**Decision:** Rejected - creates architectural anti-patterns

### Alternative 3: Use Third-Party Gateway (LiteLLM, Portkey)

**Approach:** Deploy open-source LLM gateway (LiteLLM or Portkey)

**Pros:**

- Battle-tested code
- Feature-rich (caching, fallbacks, etc.)
- Community support

**Cons:**

- ❌ Air-gapped deployment complexity (external dependencies)
- ❌ Limited customization (can't modify core logic)
- ❌ Not integrated with our auth system (ADR-049)
- ❌ Doesn't use our database schema (`models` table)
- ❌ Overkill for department scale (designed for cloud scale)
- ❌ External license dependencies

**Decision:** Rejected - doesn't fit air-gapped, department-scale, customized requirements

---

## Implementation Plan

See: `docs/development/plans/INFERENCE_GATEWAY_IMPLEMENTATION_PLAN.md`

**Timeline:** 4 weeks (3 weeks core + 1 week admin)
**Effort:** 20-25 developer-days
**Resources:** 1-2 developers (can work in parallel with roadmap)

---

## References

### Related ADRs

- **ADR-036:** Orchestrator Pipeline Pattern (business vs infrastructure separation)
- **ADR-021:** Collection-Based Document Management (embedding model immutability)
- **ADR-030:** No Transcripts; Run Manifests Only (extend for Gateway metrics)
- **ADR-049:** Unified Authentication & Security (S2S JWT, RBAC, audit)
- **ADR-051:** Provider Secrets and S2S Auth (this track)
- **ADR-052:** Model Routing and Provider Fallback (this track)
- **ADR-053:** Rate Limiting and Usage Tracking (this track)
- **ADR-054:** OpenAI Compatibility and Error Taxonomy (this track)
- **ADR-055:** Observability, Metering, and Cost Accounting (this track)

### Documentation

- Security Audit 2025-11-02 (HIGH PRIORITY: rate limiting)
- MASTER_ROADMAP.md (Phase 4.5 placement)
- PROJECT_OVERVIEW.md (department scale context)

### External References

- OpenAI API Documentation: <https://platform.openai.com/docs/api-reference>
- VLLM OpenAI-Compatible Server: <https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html>
- Redis Rate Limiting: <https://redis.io/docs/manual/patterns/rate-limiter/>

---

**Document Owner:** Architecture Team
**Last Updated:** 2025-11-02
**Status:** Approved for Implementation
