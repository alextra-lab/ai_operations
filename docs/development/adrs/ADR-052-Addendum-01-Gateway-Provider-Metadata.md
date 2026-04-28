# ADR-052 Addendum 01: Gateway Provider Metadata

**Status:** ✅ Implemented
**Date:** 2025-12-11
**Author:** AI Ops Platform Team
**Related:** ADR-052 (Model Routing and Provider Fallback)

---

## Context

**Problem:** When multiple Gateway providers are enabled (e.g., LMStudio + Ollama), the Model Registry Sync cannot automatically assign providers to discovered models because:

1. The standard OpenAI `/v1/models` response doesn't include provider information
2. Gateway aggregates models from all providers into a single response
3. Pattern matching (e.g., "mistral" → "LMStudio") is unreliable

**Impact:**
- All synced models get `provider = NULL` with multiple providers
- Requires manual provider assignment via PATCH API
- Poor user experience for multi-provider deployments

---

## Decision

**Enhance Gateway `/v1/models` response** to include provider metadata, enabling automatic provider assignment during sync.

### Implementation

#### 1. Gateway Enhancement (`inference-gateway`)

**File:** `src/inference-gateway/app/services/router.py`

```python
async def list_models_with_providers(self) -> list[dict[str, str]]:
    """
    List all routable models with their provider assignments.

    Returns:
        List of dicts with 'model_id' and 'provider' keys
    """
    if not self._loaded:
        await self.load_routes()

    return [
        {"model_id": model_id, "provider": provider_name}
        for model_id, provider_name in sorted(self._routes.items())
    ]
```

**File:** `src/inference-gateway/app/routers/chat.py`

```python
@router.get("/models")
async def list_models(...) -> JSONResponse:
    # Get list of routable models with provider assignments
    models_with_providers = await simple_router.list_models_with_providers()

    # Return OpenAI-compatible format with provider extension
    model_objects = [
        {
            "id": model["model_id"],
            "object": "model",
            "created": int(time.time()),
            "owned_by": "gateway",
            "provider": model["provider"],  # ✅ NEW
        }
        for model in models_with_providers
    ]
    ...
```

#### 2. Orchestrator Update (`orchestrator`)

**File:** `src/orchestrator/app/services/model_registry_service.py`

```python
async def sync_with_inference_server(self) -> dict[str, Any]:
    """Synchronize model registry with inference server."""
    discovered_models = await self.discover_models_from_inference_server()

    for model_data in discovered_models:
        model_id = model_data.get("id")
        provider_from_gateway = model_data.get("provider")  # ✅ NEW

        if model_id not in existing_model_map:
            created = await self._create_new_model(
                model_id,
                owned_by,
                provider_from_gateway  # ✅ NEW
            )
```

```python
async def _create_new_model(
    self,
    model_id: str,
    owned_by: str | None,
    provider_from_gateway: str | None = None  # ✅ NEW
) -> Model | None:
    """Create a new model from discovered metadata."""

    # Priority: Gateway > Auto-assign
    if provider_from_gateway:
        assigned_provider = provider_from_gateway
    else:
        assigned_provider = await self._get_default_gateway_provider()

    model_kwargs = {
        ...
        "provider": assigned_provider,  # ✅ From Gateway or auto-assigned
        ...
    }
```

---

## Response Format

### Before (Standard OpenAI):
```json
{
  "object": "list",
  "data": [
    {
      "id": "openai/gpt-oss-120b",
      "object": "model",
      "created": 1734213456,
      "owned_by": "gateway"
    }
  ]
}
```

### After (Extended):
```json
{
  "object": "list",
  "data": [
    {
      "id": "openai/gpt-oss-120b",
      "object": "model",
      "created": 1734213456,
      "owned_by": "gateway",
      "provider": "LMStudio"  // ✅ NEW
    },
    {
      "id": "llama-3.2-70b",
      "object": "model",
      "created": 1734213456,
      "owned_by": "gateway",
      "provider": "Ollama"  // ✅ NEW
    }
  ]
}
```

---

## Benefits

1. **✅ Automatic Provider Assignment:** Works with multiple providers
2. **✅ Backward Compatible:** Existing sync still works (falls back to auto-assign)
3. **✅ No Breaking Changes:** Standard OpenAI clients ignore unknown fields
4. **✅ Improved UX:** No manual PATCH calls needed
5. **✅ Scalable:** Works with any number of providers

---

## Migration Path

### Single Provider (Current):
- **Before:** Auto-assignment via `_get_default_gateway_provider()`
- **After:** Gateway explicitly provides provider name
- **Impact:** More explicit, same result

### Multiple Providers (New):
- **Before:** All models get `provider = NULL`, manual assignment required
- **After:** Each model automatically gets correct provider from Gateway
- **Impact:** Fully automated, no manual intervention

---

## Testing

### Test Scenarios:

1. **Single Provider (LMStudio only)**
   - ✅ All models correctly assigned to "LMStudio"

2. **Multiple Providers (LMStudio + Ollama)**
   - ✅ LMStudio models → provider="LMStudio"
   - ✅ Ollama models → provider="Ollama"

3. **Provider Changes**
   - ✅ Model moves from LMStudio → Ollama
   - ✅ Sync updates provider assignment

4. **Backward Compatibility**
   - ✅ Old Gateway (no provider field) → falls back to auto-assign
   - ✅ Single provider → auto-assign still works

---

## Future Enhancements

1. **Provider Health in Response:** Include provider health status
2. **Provider Capabilities:** Return supported features per provider
3. **Load Balancing Hints:** Include load/latency metrics
4. **Provider Versioning:** Track provider software versions

---

## Files Modified

### Gateway (`src/inference-gateway/`)
- ✅ `app/routers/chat.py` - Enhanced `/v1/models` to aggregate from all providers
  - Queries each enabled provider's `/v1/models` endpoint directly
  - Tags each model with `provider` (from `gateway_providers.name`) and `provider_type`
  - Returns aggregated models with provider metadata

### Orchestrator (`src/orchestrator/`)
- ✅ `app/services/model_registry_service.py` - Read provider from Gateway
  - **Fixed:** Removed `_discover_models_from_all_providers()` that bypassed Gateway
  - **Fixed:** `sync_with_inference_server()` now correctly uses Gateway via `discover_models_from_inference_server()`
  - Updated `_create_new_model()` to accept provider metadata from Gateway
  - Updated `_update_existing_model()` to use provider from Gateway
  - Fixed comments to remove false "Guaranteed" claims

### Configuration (`config/`)
- ✅ `models/model_metadata.yaml` - Fixed provider_type fields

### Tests
- ✅ `src/inference-gateway/tests/unit/test_chat_router.py` - Added tests for provider aggregation
- ✅ `src/orchestrator/tests/unit/test_model_registry_service.py` - Added tests for Gateway provider metadata usage

---

## Implementation Notes

**2025-12-11:** Fixed architecture violations where Orchestrator was bypassing Gateway abstraction. Gateway now correctly aggregates models from all providers and tags them with provider metadata. See session log: `2025-12-11-gateway-sync-architecture-fixes.md`

---

## References

- ADR-052: Model Routing and Provider Fallback
- Gateway Provider Management: `docs/api/admin/providers.md`
- Model Registry Sync: `docs/api/admin/models.md#sync-models`
- Session: `docs/development/sessions/2025-12-11-gateway-sync-architecture-fixes.md`
