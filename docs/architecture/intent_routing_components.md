# Intent-Based Routing Component Architecture

**Status:** 🟢 Active
**Last Updated:** 2025-10-12
**Related:** [ADR-016 Dynamic Intent System](../development/adrs/ADR-016-Dynamic-Intent-System.md)

This document provides detailed component diagrams showing the modular architecture of the intent-based LLM routing system.

**Evolution Note:** This architecture currently uses hardcoded intent types (QUERY, RULE_GENERATION, SUMMARIZATION, ENRICHMENT). The system is evolving to support dynamic, database-backed intent types while maintaining this component structure. See [OPTIMAL_IMPLEMENTATION_SEQUENCE.md](../development/plans/OPTIMAL_IMPLEMENTATION_SEQUENCE.md) for implementation details.

## High-Level Component Architecture

The diagram below shows the main components of the intent-based routing system and their relationships:

```mermaid
flowchart TB
    subgraph User
        UI[Frontend UI]
    end

    subgraph "Orchestration Layer"
        subgraph "Intent Processing"
            IP[Intent Parser]
            PC[Prompt Controller]
        end

        subgraph "LLM Routing System"
            LR[LLM Router]
            MS[Model Selector]
            PM[Parameter Manager]
            FS[Fallback Strategy]
            LC[LLM Client]
            RF[Response Formatter]
            PA[Prompt Assembler]
        end
    end

    subgraph "External Services"
        LLMaaS[LLM Service]
    end

    UI -->|Request| PC
    PC -->|Parse Intent| IP
    IP -->|Intent Type| PC
    PC -->|Request + Intent| LR

    LR -->|Model Selection| MS
    LR -->|Parameter Tuning| PM
    LR -->|Error Handling| FS
    LR -->|Prompt Assembly| PA
    LR -->|API Request| LC
    LR -->|Format Response| RF

    LC -->|API Call| LLMaaS
    LLMaaS -->|Raw Response| LC
    LC -->|Response Data| LR

    RF -->|Formatted Response| PC
    PC -->|Final Response| UI

    classDef primary fill:#4b97d2,stroke:#333,stroke-width:2px,color:white
    classDef secondary fill:#95cbee,stroke:#333,stroke-width:1px
    classDef external fill:#f5a742,stroke:#333,stroke-width:2px

    class LR,MS,PM,FS primary
    class IP,PC,PA,LC,RF secondary
    class LLMaaS external
```

## Component Interactions

The following sequence diagram shows the interactions between components for a typical request:

```mermaid
sequenceDiagram
    participant User
    participant Controller as Orchestrator Controller
    participant IntentParser as Intent Parser
    participant LLMRouter as LLM Router
    participant ModelSelector as Model Selector
    participant ParameterManager as Parameter Manager
    participant PromptAssembler as Prompt Assembler
    participant LLMClient as LLM Client
    participant LLMService as LLM Service
    participant FallbackStrategy as Fallback Strategy
    participant ResponseFormatter as Response Formatter

    User->>Controller: Send Request
    Controller->>IntentParser: Parse Intent
    IntentParser->>Controller: Return Intent Type
    Controller->>LLMRouter: Process Request with Intent

    LLMRouter->>ModelSelector: Select Model
    ModelSelector->>LLMRouter: Return Model Type
    LLMRouter->>ParameterManager: Get Intent Parameters
    ParameterManager->>LLMRouter: Return Optimized Parameters
    LLMRouter->>PromptAssembler: Assemble Prompt
    PromptAssembler->>LLMRouter: Return Assembled Prompt

    LLMRouter->>LLMClient: Make API Request

    alt Successful Response
        LLMClient->>LLMService: Send API Request
        LLMService->>LLMClient: Return Response
        LLMClient->>LLMRouter: Return Raw Response
        LLMRouter->>ResponseFormatter: Format Response
        ResponseFormatter->>LLMRouter: Return Formatted Response
    else API Error
        LLMClient->>LLMRouter: Return Error
        LLMRouter->>FallbackStrategy: Get Fallback Model
        FallbackStrategy->>LLMRouter: Return Fallback Model
        LLMRouter->>LLMClient: Retry with Fallback Model
        LLMClient->>LLMService: Send API Request with Fallback Model
        LLMService->>LLMClient: Return Response
        LLMClient->>LLMRouter: Return Raw Response
        LLMRouter->>ResponseFormatter: Format Response
        ResponseFormatter->>LLMRouter: Return Formatted Response
    end

    LLMRouter->>Controller: Return Final Response
    Controller->>User: Deliver Response
```

## Component Details

### LLM Router

The central coordinator that manages the request flow through all components.

```mermaid
classDiagram
    class LLMRouter {
        -LLMClient client
        -ModelSelector model_selector
        -ParameterManager parameter_manager
        -FallbackStrategy fallback_strategy
        -int max_retries
        +process(request: LLMRequest, intent_type: RequestType) LLMResponse
        +route_prompt(prompt: str, model: ModelType, temperature: float, max_tokens: int, stream: bool) Response
        -_get_response(openai_model: str, messages: List, temperature: float, max_tokens: int, model_type: ModelType) Tuple
        -_process_stream(request: LLMRequest, intent_type: RequestType) StreamingResponseGenerator
    }
```

### Model Selector

Determines the optimal model based on intent type and request characteristics.

```mermaid
classDiagram
    class ModelSelector {
        -Dict model_implementations
        -Dict intent_to_model_mapping
        +select_model(request: LLMRequest, intent_type: RequestType) ModelType
        +get_openai_model_name(model_type: ModelType) str
        -_get_from_env(key: str, default: str) str
        -_map_intent_to_model(intent_type: RequestType) ModelType
        -_analyze_prompt_content(prompt: str) ModelType
    }
```

### Parameter Manager

Applies intent-specific parameters like temperature and token limits.

```mermaid
classDiagram
    class ParameterManager {
        -Dict model_parameters
        -Dict intent_model_mapping
        +get_model_temperature(model_type: ModelType) float
        +get_model_max_tokens(model_type: ModelType) int
        +get_intent_temperature(intent_type: RequestType) float
        +get_intent_max_tokens(intent_type: RequestType) int
        -_get_float_from_env(key: str, default: float) float
        -_get_int_from_env(key: str, default: int) int
    }
```

### Fallback Strategy

Implements error recovery by selecting appropriate fallback models.

```mermaid
classDiagram
    class FallbackStrategy {
        -Dict model_fallback_mappings
        -int max_fallback_attempts
        +should_attempt_fallback(attempt: int, error: Exception) bool
        +get_fallback_model(model_type: ModelType, error: Exception, fallback_chain: List, intent_type: RequestType) ModelType
        -_get_model_type_from_env(key: str, default: ModelType) ModelType
    }
```

## Implementation Patterns

The intent-based routing system uses the following design patterns:

1. **Strategy Pattern**: Different components implement different strategies for model selection, parameter tuning, and fallback handling
2. **Dependency Injection**: Components receive their dependencies through constructor parameters
3. **Factory Pattern**: The LLMRouter acts as a factory that creates and manages all other components
4. **Chain of Responsibility**: Requests flow through a chain of components that each handle a specific aspect of processing
5. **Adapter Pattern**: The LLMClient adapts the external LLM API to the internal system requirements
