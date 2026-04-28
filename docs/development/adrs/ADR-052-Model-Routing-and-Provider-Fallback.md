# ADR-052: Model Routing and Provider Fallback

**Status:** Approved (Updated 2025-11-08)
**Date:** 2025-11-02
**Updated:** 2025-11-08 (Schema correction, no fallback)
**Deciders:** Architecture Team, Backend Team
**Tags:** architecture, reliability, providers, routing

---

## Update (2025-11-08): Schema Correction

**Changes:**

- Renamed `models.provider` → `models.provider_type` (enum: provider TYPE)
- Added `models.provider` (varchar: Gateway provider NAME for routing)
- Removed fallback logic - one-way migration to Gateway for v1 release
- Local models (`provider=NULL`) handled by Embedding Service, not Gateway

**Rationale:**

- Original schema stored provider TYPE in `provider` field, preventing multiple OpenAI-compatible providers
- Correct architecture: `provider_type` = API compatibility, `provider` = specific instance name
- Example: `provider_type='openai'` with `provider='LMStudio'` or `provider='Ollama'`

---

## Context

The Inference Gateway must route requests to appropriate providers based on model selection. The routing strategy impacts reliability, performance, and future extensibility. The application operates at **department scale** (10-100 users) with flexibility to scale.

### Requirements

**Functional:**

- Route chat completion requests to correct provider (OpenAI, Mistral, LMStudio, VLLM)
- Support local and remote providers
- Handle provider failures gracefully
- Provide clear error messages when routing fails

**Non-Functional:**

- Simple to understand and debug (operations team visibility)
- Fast routing decision (<1ms)
- Extensible to new providers without code changes
- Future-ready for smart routing (cost optimization, load balancing)

### Critical Constraint (ADR-021)

**Embedding Models = Concrete IDs (No Aliases):**

Collections use **immutable, concrete model IDs** for embeddings:

```python
# Collection schema (MUST NOT change)
class Collection:
    embedding_model: str = "text-embedding-3-small"  # CONCRETE, not alias
    embedding_dimensions: int = 1536
```

**Why:** Different embedding models produce incomparable vector spaces. Changing model = must re-embed entire collection (expensive, risky). See ADR-021 for full rationale.

**Implication:** Model routing for embeddings is simple provider lookup (no aliasing, no smart routing).

### Existing Patterns

**Orchestrator Model Selection (Keep):**

```python
# src/orchestrator/app/orchestrator/llm_router.py
def select_model(self, intent_type: RequestType) -> str:
    """Business logic: Intent → Model."""
    if intent_type == RequestType.QUERY:
        return "gpt-4o-mini"  # Fast, cheap
    elif intent_type == RequestType.SUMMARIZE:
        return "gpt-4o"  # Better quality
    # Returns CONCRETE model ID
```

**Gateway Responsibility (New):**

- Receive concrete model ID from orchestrator
- Route to correct provider
- Handle provider failures
- Track usage/cost

---

## Decision

Implement **two-version strategy**: Simple routing (v1) with extensibility pattern for smart routing (v2+).

### Version 1 (MVP): Simple Provider Lookup

**Implementation: Dictionary-Based Routing**

```python
# src/inference-gateway/app/routing/simple_router.py

PROVIDER_MAP = {
    # OpenAI models
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gpt-4-turbo": "openai",
    "gpt-3.5-turbo": "openai",

    # Mistral models
    "mistral-large-latest": "mistral",
    "mistral-small-latest": "mistral",
    "codestral-latest": "mistral",

    # Local models (LMStudio/Ollama/vLLM)
    "local/llama-3.1-8b": "lmstudio",
    "local/llama-3.1-70b": "lmstudio",
    "local/mistral-7b": "lmstudio",

    # Embedding models
    "text-embedding-3-large": "openai",
    "text-embedding-3-small": "openai",
    "text-embedding-ada-002": "openai",
    # Local embeddings handled by Embedding Service (not Gateway)
}

class SimpleRouter:
    """V1: Direct model → provider mapping."""

    def __init__(self, provider_manager: ProviderManager):
        self.provider_manager = provider_manager
        self.model_map = PROVIDER_MAP.copy()

    def route(self, model: str) -> Provider:
        """
        Route model to provider.

        Args:
            model: Concrete model ID (e.g., "gpt-4o-mini")

        Returns:
            Provider instance

        Raises:
            ModelNotFoundError: Model not in routing table
            ProviderUnavailableError: Provider exists but disabled/unhealthy
        """
        provider_name = self.model_map.get(model)

        if not provider_name:
            raise ModelNotFoundError(
                f"Model '{model}' not found. "
                f"Available models: {list(self.model_map.keys())}"
            )

        provider = self.provider_manager.get_provider(provider_name)

        if not provider or not provider.enabled:
            raise ProviderUnavailableError(
                f"Provider '{provider_name}' for model '{model}' is unavailable. "
                f"Available providers: {self.provider_manager.list_enabled()}"
            )

        return provider
```

**Configuration Source:**

```python
# Load from database on startup
def load_model_routes(db: Session) -> dict[str, str]:
    """Load model → provider mapping from database."""

    # Join models table with gateway_providers
    routes = db.execute(
        """
        SELECT m.model_id, gp.name as provider_name
        FROM models m
        JOIN gateway_providers gp ON m.provider = gp.name
        WHERE m.is_active = true AND gp.enabled = true
        """
    ).fetchall()

    return {row.model_id: row.provider_name for row in routes}

# Merge with static defaults
PROVIDER_MAP = {
    **load_model_routes(db),
    **STATIC_FALLBACKS  # Hardcoded for air-gapped/offline
}
```

### Version 2 (Future): Smart Router with Strategy Pattern

**Implementation: Pluggable Router Interface**

```python
# src/inference-gateway/app/routing/router.py

class Router(Protocol):
    """Router interface for extensibility."""

    def route(self, model: str, context: RequestContext | None = None) -> Provider:
        """Route model to provider with optional context."""
        ...

class SimpleRouter(Router):
    """V1: Dictionary lookup (current implementation)."""

    def route(self, model: str, context: RequestContext | None = None) -> Provider:
        # Ignores context, just does lookup
        return self._lookup_provider(model)

class SmartRouter(Router):
    """V2: Context-aware routing (future)."""

    def route(self, model: str, context: RequestContext | None = None) -> Provider:
        """
        Route with context (cost optimization, load balancing).

        Context attributes:
          - intent_type: "QUERY", "SUMMARIZE", etc.
          - cost_limit: Max EUR per request
          - latency_target: Max ms for response
          - user_tier: "free", "premium", etc.
        """
        candidates = self._get_providers_for_model(model)

        if context and context.cost_limit:
            # Filter by cost
            candidates = [p for p in candidates if p.cost_per_request < context.cost_limit]

        if context and context.latency_target:
            # Prefer low-latency providers
            candidates = sorted(candidates, key=lambda p: p.avg_latency_ms)

        # Return best candidate
        return candidates[0] if candidates else self._fallback_provider(model)

# Configuration-driven router selection
ROUTER_TYPE = os.getenv("GATEWAY_ROUTER_TYPE", "simple")  # or "smart"

if ROUTER_TYPE == "simple":
    router = SimpleRouter(provider_manager)
else:
    router = SmartRouter(provider_manager)
```

**Future Smart Router Features:**

1. **Cost Optimization:** Pick cheapest provider for equivalent models
2. **Load Balancing:** Distribute requests across multiple provider instances
3. **Latency Optimization:** Prefer local providers for time-sensitive requests
4. **Health-Aware:** Avoid degraded providers automatically
5. **Fallback Chains:** Try Provider A → B → C on failures

**When to Upgrade to V2:**

- Multiple providers offer same model (e.g., GPT-4o on OpenAI + Azure)
- Cost optimization becomes priority (save 20%+ on inference)
- Need load balancing (single provider saturated)
- Geographic routing (EU data residency requirements)

### Provider Fallback (Light Implementation)

**V1 Approach: Retry with Exponential Backoff**

```python
# src/inference-gateway/app/providers/client.py
import backoff

class ProviderClient:
    """Base provider client with retry logic."""

    @backoff.on_exception(
        backoff.expo,
        (Timeout, ConnectionError, HTTPError),
        max_tries=2,  # Provider call × 2 = 20 seconds max
        max_value=10,
        on_backoff=lambda details: logger.warning(
            f"Provider retry attempt {details['tries']}, "
            f"waiting {details['wait']:.1f}s"
        )
    )
    async def call_provider(
        self,
        endpoint: str,
        payload: dict
    ) -> dict:
        """Call provider with retry logic."""

        try:
            response = await self.http_client.post(
                endpoint,
                json=payload,
                timeout=10.0  # 10 second timeout
            )
            response.raise_for_status()
            return response.json()

        except Timeout as e:
            logger.error(f"Provider timeout after 10s: {e}")
            raise ProviderTimeoutError(
                f"Provider {self.name} did not respond within 10 seconds"
            ) from e

        except ConnectionError as e:
            logger.error(f"Provider connection failed: {e}")
            raise ProviderConnectionError(
                f"Cannot connect to provider {self.name}"
            ) from e

        except HTTPError as e:
            if e.response.status_code == 429:
                # Rate limited by provider
                raise ProviderRateLimitError(
                    f"Provider {self.name} rate limit exceeded",
                    retry_after=int(e.response.headers.get("Retry-After", 60))
                ) from e
            else:
                raise ProviderHTTPError(
                    f"Provider {self.name} returned {e.response.status_code}"
                ) from e
```

**V2 Approach: Fallback Chains (Future)**

```python
class SmartRouter:
    def route_with_fallback(
        self,
        model: str,
        context: RequestContext
    ) -> Provider:
        """Route with automatic fallback chain."""

        # Define fallback chain
        chain = [
            ("openai", "gpt-4o-mini"),      # Primary
            ("mistral", "mistral-small"),   # Secondary (cheaper)
            ("lmstudio", "local/llama-3.1") # Tertiary (offline)
        ]

        for provider_name, fallback_model in chain:
            provider = self.provider_manager.get_provider(provider_name)

            if provider and provider.enabled and provider.is_healthy:
                context.fallback_used = (provider_name != chain[0][0])
                context.actual_model = fallback_model
                return provider

        # All providers failed
        raise AllProvidersUnavailableError(
            f"No available providers for model '{model}'"
        )
```

---

## Rationale

### Why Simple Router for V1?

**Complexity vs Value:**

```
Simple Router (v1):
  Code: ~200 lines
  Complexity: Dictionary lookup (O(1))
  Latency: <1ms
  Test coverage: 100% (simple logic)

Smart Router (v2):
  Code: ~1,000 lines
  Complexity: Multi-criteria optimization
  Latency: 5-10ms (decision overhead)
  Test coverage: 70% (many edge cases)

Value at department scale (100 users):
  Cost savings: ~€50/month (5% of budget)
  Latency improvement: Negligible (both providers fast)
  Operational complexity: 5x higher

Verdict: V1 sufficient, V2 when cost optimization matters
```

**Orchestrator Already Smart:**

- Orchestrator does intent-aware selection (QUERY → cheap model)
- Gateway doing same thing = duplicate logic
- Keep business logic in orchestrator, infrastructure in Gateway

### Why No Embedding Aliases?

**Vector Space Immutability:**

```python
# WRONG: Alias allows changing underlying model
collection.embedding_model = "soc_default_embed"  # Alias
# Admin changes alias: "soc_default_embed" → "text-embedding-ada-002"
# New documents embedded with ada-002
# Old documents embedded with 3-small
# INCOMPATIBLE VECTOR SPACES → Search fails

# CORRECT: Concrete model ID (immutable)
collection.embedding_model = "text-embedding-3-small"  # Concrete
# Cannot change without re-embedding entire collection
# Vector space consistency guaranteed
```

**Chat Models OK for Aliases (Future):**

- Chat models perform same task (generate text)
- Changing model changes quality/cost, not fundamental capability
- Alias allows swapping without changing use cases
- Example: `soc_default_gpt` → `gpt-4o-mini` (save money) or `gpt-4o` (better quality)

### Why Strategy Pattern?

**Future-Proofing:**

```python
# Add new router without changing callers
class GeoRouter(Router):
    """Route based on data residency (EU vs US)."""

    def route(self, model: str, context: RequestContext) -> Provider:
        if context.user_region == "EU":
            return self.eu_providers[model]
        else:
            return self.us_providers[model]

# Swap router via config
router = GeoRouter(provider_manager)  # No code changes in Gateway endpoints
```

**Open/Closed Principle:**

- Open for extension (new router types)
- Closed for modification (Gateway endpoint code unchanged)

---

## Consequences

### Positive

✅ **Simplicity:** V1 is ~200 lines, easy to understand and debug
✅ **Performance:** <1ms routing decision (dictionary lookup)
✅ **Testability:** Simple logic, 100% test coverage achievable
✅ **Maintainability:** Adding new model = 1 line in config
✅ **Extensibility:** Strategy pattern allows V2 upgrade without breaking changes
✅ **Reliability:** Simple code = fewer bugs

### Negative

❌ **No Cost Optimization:** Can't automatically pick cheapest provider (manual config)
❌ **No Load Balancing:** Can't distribute load across providers (single provider per model)
❌ **No Automatic Failover:** Must manually configure fallback (no chain)

### Mitigation

**Cost Optimization:**

- Orchestrator picks cheap models based on intent (already doing this)
- Admin manually configures model → provider mapping for best value
- V2 smart router adds automatic optimization when needed

**Load Balancing:**

- Single provider per model sufficient for department scale
- Provider handles internal load balancing (OpenAI has multiple regions)
- V2 adds multi-provider support when traffic increases

**Failover:**

- Retry logic (2 attempts) handles transient failures
- Circuit breaker (ADR-050) prevents cascade failures
- V2 fallback chains add automatic provider switching

---

## Implementation Notes

### Model Registry Integration

**Use Existing `models` Table:**

```sql
-- Current schema (as of 2025-11-08)
CREATE TABLE models (
    id UUID PRIMARY KEY,
    model_id TEXT UNIQUE NOT NULL,        -- "gpt-4o-mini"
    provider_type model_provider_enum NOT NULL,  -- "openai", "azure", "mistral", "anthropic", "local"
    provider VARCHAR(255),                 -- Gateway provider name: "LMStudio", NULL for local
    is_available BOOLEAN DEFAULT true,
    context_window INTEGER,
    max_output_tokens INTEGER,
    supports_tools BOOLEAN,
    supports_vision BOOLEAN,
    -- Cost tracking
    input_price_per_million NUMERIC(10, 4),
    output_price_per_million NUMERIC(10, 4)
);

-- Gateway queries this table for routing
SELECT m.model_id, gp.name as provider_name
FROM models m
INNER JOIN gateway_providers gp ON m.provider = gp.name
WHERE m.is_available = true AND gp.is_enabled = true;
```

**Sync Gateway Routes:**

```python
# Gateway startup - SimpleRouter auto-loads from database
async def initialize_router():
    """Load model routes from database."""

    # SimpleRouter queries database on first route() call
    # No static fallbacks - all models come from sync process
    return SimpleRouter()

# Admin syncs models from LMStudio
POST /api/v1/models/sync  # Queries each Gateway provider's /v1/models
# Creates models with:
# - provider_type = Gateway provider's type enum
# - provider = Gateway provider's name (for routing)

# Gateway SimpleRouter loads routes:
SELECT m.model_id, gp.name
FROM models m
JOIN gateway_providers gp ON m.provider = gp.name
WHERE m.is_available = true AND gp.is_enabled = true;

# Result: {"mistral-7b-instruct": "LMStudio", ...}
```

### Provider Health Checks

**Lightweight Health Monitoring:**

```python
class Provider:
    """Provider instance with health tracking."""

    def __init__(self, config: ProviderConfig):
        self.name = config.name
        self.base_url = config.base_url
        self.enabled = config.enabled
        self._health_status = "unknown"  # unknown, healthy, degraded, down
        self._last_success = None
        self._last_failure = None
        self._failure_count = 0

    @property
    def is_healthy(self) -> bool:
        """Simple health check (no proactive probing)."""

        # Provider disabled
        if not self.enabled:
            return False

        # Never tested yet
        if not self._last_success and not self._last_failure:
            return True  # Optimistic (assume healthy until proven otherwise)

        # Recent success
        if self._last_success and self._last_success > time.time() - 300:
            return True  # Healthy if success within 5 minutes

        # Recent failures
        if self._failure_count >= 3:
            return False  # Degraded after 3 failures

        return True  # Default to healthy

    def record_success(self):
        """Record successful request."""
        self._last_success = time.time()
        self._failure_count = 0
        self._health_status = "healthy"

    def record_failure(self):
        """Record failed request."""
        self._last_failure = time.time()
        self._failure_count += 1

        if self._failure_count >= 3:
            self._health_status = "degraded"
            logger.warning(
                f"Provider {self.name} marked as degraded "
                f"({self._failure_count} consecutive failures)"
            )
```

**Health Status Endpoint:**

```python
@router.get("/admin/gateway/health")
async def get_health_status(
    token: TokenPayload = Depends(requires_scope("gateway:admin"))
):
    """Get provider health status."""

    providers = provider_manager.list_all()

    return {
        "providers": [
            {
                "name": p.name,
                "enabled": p.enabled,
                "health_status": p._health_status,
                "last_success": p._last_success,
                "last_failure": p._last_failure,
                "failure_count": p._failure_count,
                "is_healthy": p.is_healthy
            }
            for p in providers
        ]
    }
```

---

## Acceptance Criteria

### V1 (Simple Router)

✅ Model → provider mapping loaded from `models` table
✅ Routing decision completes in <1ms (p95)
✅ Unknown model returns clear error with available models list
✅ Disabled provider returns error with available providers
✅ Admin can add new model without code changes (DB insert + reload)
✅ Retry logic handles transient failures (2 attempts, exponential backoff)
✅ Provider health tracked (success/failure counts)

### V2 (Smart Router - Future)

📋 Multiple routing strategies selectable via config
📋 Cost optimization router picks cheapest equivalent model
📋 Load balancing router distributes across provider instances
📋 Fallback chains automatically switch providers on failure
📋 Geographic router respects data residency requirements

---

## Migration Path

### Current → V1 (Gateway Deployment)

**Before:**

```python
# Orchestrator calls OpenAI directly
response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages
)
```

**After (V1):**

```python
# Orchestrator calls Gateway (looks identical)
response = gateway_client.chat_completion(
    model="gpt-4o-mini",  # Gateway routes to OpenAI
    messages=messages
)
```

**Changes Required:**

- Update `LLMAAS_BASE_URL` (if present) to the Gateway for compatibility
- Provide `INFERENCE_GATEWAY_URL` to the orchestrator
- Zero code changes (OpenAI-compatible API)

### V1 → V2 (Smart Router Upgrade)

**Before (V1):**

```python
GATEWAY_ROUTER_TYPE=simple
# Uses SimpleRouter (dictionary lookup)
```

**After (V2):**

```python
GATEWAY_ROUTER_TYPE=smart
# Uses SmartRouter (context-aware)
```

**Changes Required:**

- Set environment variable
- Configure routing policies (DB or config file)
- Test fallback chains
- Zero code changes in callers (Strategy Pattern)

---

## References

### Related ADRs

- **ADR-021:** Collection-Based Document Management (embedding model immutability)
- **ADR-050:** Inference Gateway and Responsibility Split (routing responsibility)
- **ADR-051:** Provider Secrets and S2S Auth (provider configuration)
- **ADR-053:** Rate Limiting and Usage Tracking (provider limits)

### Existing Code

- `src/orchestrator/app/orchestrator/llm_router.py` - Intent-aware model selection
- `src/orchestrator/app/db/models.py` - `models` table schema
- `src/embedding/app/providers/factory.py` - Provider abstraction pattern

### External References

- Strategy Pattern: <https://refactoring.guru/design-patterns/strategy>
- Circuit Breaker Pattern: <https://martinfowler.com/bliki/CircuitBreaker.html>

---

**Document Owner:** Architecture Team
**Last Updated:** 2025-11-02
**Status:** Approved for V1 Implementation
