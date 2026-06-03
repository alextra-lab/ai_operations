# orchestrator-api

Central FastAPI backend for the AI Operations Platform. Handles RAG query pipelines, admin
operations, MCP tool wiring, and WebSocket/SSE streaming. Exposed on port **18000 → 8000**.

## Role in the platform

Every user query flows through the orchestrator:

```
Client → orchestrator-api → [llm-guard-svc] → inference-gateway → LLM
                          → corpus-service (retrieval)
```

It owns intent parsing, model selection, prompt assembly, retrieval injection, and response
streaming. Admin, use-case management, and tooling APIs are also served here.

## Pipeline

The pipeline uses the **Step protocol** (ADR-036): each step receives a `RequestContext` and
returns an updated one. `UseCaseRunner` composes and executes steps sequentially.

```
controller.py  →  UseCaseRunner.run(ctx)
                      │
                      ├─ GuardValidate       (llm-guard-svc, if enabled)
                      ├─ RetrieveContext     (corpus-service vector search)
                      ├─ AssemblePrompt      (template + retrieved chunks)
                      ├─ ExecuteLLM          (inference-gateway, streaming)
                      ├─ FormatResponse      (output template rendering)
                      └─ RecordHistory       (query history, run manifest)
```

### Key classes

| Class | File | Role |
|---|---|---|
| `Orchestrator` | `app/orchestrator/controller.py` | Entry point; builds `RequestContext`, dispatches to runner |
| `UseCaseRunner` | `app/orchestrator/runner.py` | Executes the ordered step list; captures telemetry |
| `Step` | `app/orchestrator/runner.py` | Protocol: `async def run(ctx) -> ctx` |
| `IntentParser` | `app/orchestrator/intent_parser.py` | Parses `request_type` into `IntentResponse` |
| `ModelSelector` | `app/orchestrator/model_selection.py` | Looks up `intent_model_defaults` table (ADR-069); raises if unconfigured |
| `LLMRouter` | `app/orchestrator/llm_router.py` | Routes to inference-gateway; handles streaming vs. unary |
| `PromptAssembler` | `app/orchestrator/prompt_assembler.py` | Maps intent → template ID, fills variables |
| `TemplateEngine` | `app/orchestrator/template_engine.py` | Loads use-case config and prompts from DB |
| `StreamingResponseGenerator` | `app/orchestrator/streaming_response.py` | Async iterator wrapping OpenAI-compatible streaming chunks |

### Intent → model flow

1. `IntentParser.parse_intent()` resolves `detected_type` from the request (deterministic in
   current implementation).
2. `ModelSelector.get_model_for_intent(intent_code)` queries the `intent_model_defaults` DB table.
   Use-case pin wins; intent default is the fallback. No hardcoded model names — raises `ValueError`
   if no default is configured.

## MCP tool wiring

MCP clients live in `app/mcp/` and support two transports:

- **HTTP** — `http_client.py` (implements `MCPClient`)
- **STDIO** — `stdio_client.py` (implements `MCPClient`)

Protocol serialization (JSON-RPC 2.0) is in `protocol_handler.py`.

Tools are registered at startup via `ToolRegistry` and validated against per-use-case allowlists
by `ToolValidator` (ADR-057). An empty allowlist permits all tools; a non-empty one restricts to
the listed names.

```
app/orchestrator/tool_registry.py   — ToolRegistry, ToolMetadata, ToolCategory
app/orchestrator/tool_validator.py  — ToolValidator.validate_tool_call(name, allowlist)
```

## Routers

40+ FastAPI routers in `app/routers/`. Notable ones:

| Router | Purpose |
|---|---|
| `orchestrator.py` | Main pipeline endpoints (query, stream) |
| `websocket.py` | WebSocket support |
| `use_cases.py` | Use case discovery (RBAC-filtered) |
| `use_case_management.py` | Use case CRUD & versioning (admin) |
| `tools_admin.py` / `tools_developer.py` | Tool registry management |
| `admin_intent_models.py` | Intent-to-model defaults (ADR-069) |
| `admin_config.py` | System configuration (JSONB) |
| `query_history.py` | Query history with RLS |
| `health.py` | Health checks |

## Configuration

Config is loaded via `shared.config.loader.load_orchestrator_config()` and cached on
`app.state`. Key environment variables (set in `config/env/.env`):

| Variable | Default | Description |
|---|---|---|
| `INFERENCE_GATEWAY_URL` | `http://inference-gateway:8002` | LLM proxy |
| `RETRIEVAL_SERVICE_URL` | `http://corpus-service:8001/api/v1` | Vector retrieval |
| `LLM_GUARD_ENABLED` | `false` | Enable prompt safety scanning |
| `LLM_GUARD_URL` | `http://llm-guard-svc:8081` | Guard service URL |
| `LLM_GUARD_TIMEOUT` | `10.0` | Guard timeout (seconds) |
| `CONFIDENCE_THRESHOLD` | `0.7` | Minimum response confidence |
| `MIN_RELEVANCY_SCORE` | `0.3` | Minimum retrieval similarity |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Testing

```bash
# All orchestrator tests
bash src/orchestrator/run_tests.sh

# With coverage
bash src/orchestrator/run_tests.sh --cov=app --cov-report=term-missing

# Or via the centralised runner
python ops/testing/run_all_tests.py --component orchestrator
```

Tests live in `src/orchestrator/tests/unit/` and `tests/integration/`.
