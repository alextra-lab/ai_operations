# Intent-Based LLM Routing

This document describes the intent-based LLM routing implementation in the AI Operations Platform system.

## Overview

The Intent-Based LLM Routing system is a modular orchestration layer that uses request intent types as a primary factor for model selection, parameter tuning, and fallback strategies. It enhances the orchestrator workflow by making model selection more aligned with business use cases.

## Modular Architecture

The system is composed of the following modular components:

- **LLMRouter**: Core component that coordinates model selection, parameter management, and fallback strategies
- **ModelSelector**: Determines the optimal model using use-case overrides, DB defaults, and request context
- **ParameterManager**: Applies code-level defaults from `ModelType.metadata` when DB values are missing
- **FallbackStrategy**: Implements intent-aware fallback mechanisms for error recovery

```
┌─────────────┐     ┌────────────────┐
│             │     │                │
│ IntentParser├────►│  LLMRouter     │
│             │     │                │
└─────────────┘     └─┬──────┬───────┘
                      │      │
      ┌───────────────┘      │
      │                      │
┌─────▼──────┐      ┌────────▼───────┐
│            │      │                │
│ModelSelector│      │ParameterManager│
│            │      │                │
└────────────┘      └────────┬───────┘
                             │
                     ┌───────▼──────┐
                     │              │
                     │FallbackStrategy│
                     │              │
                     └──────────────┘
```

## Key Features

- **Intent-Based Model Mapping**: Maps intent types (QUERY, RULE_GENERATION, etc.) to appropriate models
- **Database-Driven Configuration**: Uses `intent_model_defaults` as the source of truth (ADR-069)
- **Intent-Specific Parameters**: Applies intent-optimized temperature and token settings
- **Enhanced Fallback Mechanisms**: Uses intent-specific fallback strategies for model failures
- **Comprehensive Metadata**: Tracks intent information throughout the response lifecycle

## Configuration

Intent routing configuration is database-driven:

- Model defaults are stored in `intent_model_defaults`.
- Temperature defaults are stored in `intent_model_defaults.temperature`.
- Use-case authoring can override model/temperature per use case.
- `ParameterManager` provides code-level defaults when DB values are not set.

### Fallback Configuration

```yaml
# Model fallback mappings
- FALLBACK_MODEL_QUERY=SUMMARIZATION
- FALLBACK_MODEL_RULE_GENERATION=ENRICHMENT
- FALLBACK_MODEL_SUMMARIZATION=QUERY
- FALLBACK_MODEL_ENRICHMENT=RULE_GENERATION
```

## Model Selection Logic

The `ModelSelector` uses the following priority order for model selection:

1. **Explicit model preference** in the request (if provided)
2. **Intent type** for intent-specific model mapping
3. **Prompt characteristics** (length, complexity) as a fallback

## Usage in Code

The modular components work together seamlessly:

```python
# Import the router and necessary schemas
from app.orchestrator.llm_router import LLMRouter
from app.schemas.intent import RequestType
from app.schemas.llm import LLMRequest

# Create the router instance (automatically initializes all components)
router = LLMRouter(
    api_key="your_api_key",
    base_url="https://api.openai.com/v1"
)

# Create an LLM request
request = LLMRequest(
    prompt="Analyze this security event",
    temperature=0.7,
    max_tokens=1024
)

# Process a request with intent type (non-streaming)
response = router.process(
    request=request,
    intent_type=RequestType.QUERY
)

# Process a request with streaming
for chunk in router.process(
    request=request,
    intent_type=RequestType.QUERY,
    stream=True
):
    print(chunk)
```

## Component Integration Flow

The intent-based routing system integrates with the orchestrator controller in this sequence:

```
IntentParser (detects intent) →
  Orchestrator Controller (passes intent) →
    LLMRouter (coordinates components) →
      ModelSelector (selects model based on intent) →
      ParameterManager (applies intent-specific parameters) →
      API Call →
      FallbackStrategy (handles errors if needed) →
        Response to Client
```

## Component Details

### LLMRouter

The central coordinator that:
- Initializes and manages all components
- Processes incoming requests
- Applies intent-specific parameters
- Handles streaming and non-streaming responses
- Manages error handling and fallbacks

### ModelSelector

Responsible for:
- Mapping intent types to model types
- Selecting the optimal model based on intent and request content
- Converting model types to implementation-specific model names
- Supporting explicit model preferences in requests

### ParameterManager

Manages parameters like:
- Intent-specific temperature settings
- Intent-specific token limits
- Default parameter values when not explicitly set
- Parameter validation and normalization

### FallbackStrategy

Implements error recovery by:
- Determining if fallback should be attempted
- Selecting appropriate fallback models based on intent
- Tracking fallback attempts to prevent loops
- Handling different error types with appropriate strategies

## Default Values

If not specified in use-case config or database defaults, the system uses these code defaults:

- **ModelSelector Defaults**:
  - QUERY: gpt-4.1-nano
  - RULE_GENERATION: gpt-4.1-mini
  - SUMMARIZATION: gpt-4.1-mini
  - ENRICHMENT: gpt-4.1-mini

- **ParameterManager Defaults**:
  - QUERY: temperature 0.8, 3000 tokens
  - RULE_GENERATION: temperature 0.3, 5000 tokens
  - SUMMARIZATION: temperature 0.5, 6144 tokens
  - ENRICHMENT: temperature 0.6, 8192 tokens

## Data Flow Diagram

The following diagram illustrates the data flow through the system:

```
                 ┌─────────────────────┐
                 │                     │
                 │  Request + Intent   │
                 │                     │
                 └──────────┬──────────┘
                            │
                            ▼
┌───────────────────────────────────────────────┐
│                                               │
│                  LLMRouter                    │
│                                               │
└───┬─────────────────┬──────────────────┬──────┘
    │                 │                  │
    ▼                 ▼                  ▼
┌──────────┐  ┌──────────────┐  ┌─────────────────┐
│          │  │              │  │                 │
│Model Type│  │Parameters    │  │Fallback Strategy│
│          │  │              │  │                 │
└────┬─────┘  └────┬─────────┘  └────────┬────────┘
     │            │                      │
     ▼            ▼                      ▼
┌────────────────────────────────────────────────┐
│                                                │
│                 LLM API Call                   │
│                                                │
└────────────────────┬───────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│                                                │
│     Formatted Response with Intent Metadata    │
│                                                │
└────────────────────────────────────────────────┘
```

## Future Extensions

This modular architecture facilitates extension in several ways:

1. **New Model Types**: Add new model types by extending the ModelType enum and updating the ModelSelector
2. **New Intent Types**: Add new intent types by extending the RequestType enum
3. **Enhanced Parameter Management**: Add new parameters by extending the ParameterManager
4. **Custom Fallback Strategies**: Implement specialized fallback strategies for different error conditions
5. **Tool-Specific Routing**: Extend the ModelSelector to support granular tool-specific model selection

```yaml
# Future tool-specific model mapping (example)
- TOOL_MODEL_THREAT_INTEL_LOOKUP=gpt-4.1-mini
- TOOL_MODEL_CVE_ANALYSIS=gpt-4.1-mini
- TOOL_MODEL_YARA_RULE_GENERATION=gpt-4.1-mini
- TOOL_MODEL_IOC_EXTRACTION=gpt-4.1-nano
