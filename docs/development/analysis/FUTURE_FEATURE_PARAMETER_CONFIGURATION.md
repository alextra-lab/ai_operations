# Future Feature: UI Parameter Configuration for Semantic Search and RAG Q&A

## Overview

Add UI controls to allow developers and corpus managers to configure and test RAG/retrieval parameters in real-time without modifying use case configurations.

## Current State (Backend Ready)

The backend **already supports** parameter passing via the `context` dictionary in `/api/v1/process`:

```json
{
  "query": "What is authentication?",
  "context": {
    "top_k": 15,
    "similarity_threshold": 0.4,
    "temperature": 0.8,
    "model_preference": "gpt-4",
    "rag_mode": true,
    "use_case_id": "custom-query",
    "max_context_length": 4000
  }
}
```

### Parameters Currently Supported

#### RAG/Retrieval Parameters (Working)
- **`top_k`** - Number of documents to retrieve (default: 10)
- **`similarity_threshold`** - Minimum similarity score (default: 0.6)

These are read in `controller.py` lines 455-466 when no use case config is provided.

#### LLM Parameters (Needs Implementation)
- **`temperature`** - LLM temperature (0.0-1.0)
- **`model_preference`** - LLM model to use
- **`max_tokens`** - Maximum output tokens

These need to be implemented in the LLM router to check `context` before using defaults.

#### Other Parameters
- **`embedding_model`** - Embedding model override (partially working)
- **`rag_mode`** - Enable/disable RAG (already used)
- **`use_case_id`** - Load specific use case configuration

## What Needs to Be Done

### Backend Updates

1. **Controller (orchestrator/controller.py)**
   - Update retrieval parameter logic to prioritize `context` overrides:
     ```python
     # Priority: context > use_case_config > defaults
     top_k = context.get("top_k") if context else None
     if top_k is None and use_case_config:
         top_k = use_case_config.rag.top_k
     if top_k is None:
         top_k = self._get_top_k_for_intent(intent_type)
     ```

2. **LLM Router (orchestrator/llm_router.py)**
   - Add support for reading LLM parameters from metadata/context:
     ```python
     temperature = metadata.get("temperature", 0.7)
     model = metadata.get("model_preference", default_model)
     max_tokens = metadata.get("max_tokens", 2048)
     ```

3. **Response Formatter**
   - Include applied parameters in metrics for transparency

### Frontend Updates

#### 1. Semantic Search Page (Developer Tool)
Add expandable "Advanced Parameters" section with:
- **Top K** slider (1-50, default: 10)
- **Similarity Threshold** slider (0.0-1.0, default: 0.6)
- **Embedding Model** dropdown (list available models)

#### 2. RAG Q&A Page (Developer Tool)
Add expandable "Advanced Parameters" section with:
- **Top K** slider (1-50, default: 10)
- **Similarity Threshold** slider (0.0-1.0, default: 0.6)
- **Temperature** slider (0.0-1.0, default: 0.7)
- **Model** dropdown (list available LLM models)
- **Max Context Length** input (tokens)

#### 3. UI Component Structure
```typescript
interface QueryParameters {
  // Retrieval
  top_k?: number;
  similarity_threshold?: number;
  embedding_model?: string;

  // LLM
  temperature?: number;
  model_preference?: string;
  max_tokens?: number;
  max_context_length?: number;
}

// In service call:
const request = {
  query: this.query,
  context: {
    ...this.advancedParameters  // Spread user-configured params
  }
};
```

### Implementation Plan

#### Phase 1: Backend Support (1-2 days)
1. Update controller to prioritize context parameters
2. Update LLM router to accept context parameters
3. Add parameter validation
4. Update metrics to show applied parameters
5. Write unit tests

#### Phase 2: Frontend UI (2-3 days)
1. Create `AdvancedParametersComponent` (reusable)
2. Add to Semantic Search page
3. Add to RAG Q&A page
4. Add parameter presets (e.g., "Strict", "Balanced", "Exploratory")
5. Add "Reset to Defaults" button

#### Phase 3: Testing & Documentation (1 day)
1. Test parameter combinations
2. Document recommended values
3. Add tooltips/help text in UI
4. Update API documentation

### Benefits

1. **For Developers:**
   - Test chunking strategies by adjusting `top_k` and `similarity_threshold`
   - Compare different embedding models
   - Fine-tune LLM parameters for specific queries

2. **For Corpus Managers:**
   - Validate retrieval quality with different thresholds
   - Identify optimal parameters before creating use cases

3. **For Use Case Creators:**
   - Test parameter combinations before committing to use case config
   - Copy working parameters to use case configuration

### Notes

- These parameters should be **developer tools only** - not exposed to end users
- Consider adding "Save as Use Case" button to create use case from tested parameters
- Add parameter validation to prevent invalid combinations
- Log parameter usage for analysis

## Related Files

- Backend: `src/orchestrator/app/orchestrator/controller.py`
- Backend: `src/orchestrator/app/orchestrator/llm_router.py`
- Frontend: `src/frontend-angular/src/app/pages/query/semantic-search.component.ts`
- Frontend: `src/frontend-angular/src/app/pages/query/rag-qa.component.ts`
