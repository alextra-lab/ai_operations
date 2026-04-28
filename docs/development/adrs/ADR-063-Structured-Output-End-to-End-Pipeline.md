# ADR-063: Structured Output End-to-End Pipeline

**Status:** Proposed
**Date:** 2026-02-04
**Deciders:** AI Operations Platform Team
**Tags:** structured-output, json-schema, visualization, llm, response-format

---

## Context

**What is the issue we're addressing?**

The AI Operations Platform has infrastructure for structured output that is partially implemented but not connected end-to-end:

### What Exists (Backend)

1. **OutputContractConfig** (`use_case_config.py`) - Defines output format, schema, validation mode
2. **ResponseFormatter** (`response_formatter.py`) - Validates LLM output against schema
3. **Validation modes** - `best_effort` and `strict`

### What Exists (Frontend)

1. **StructuredOutputRendererComponent** - Dynamically selects visualizers
2. **Visualizer components** - Table, Chart, Gauge, Timeline
3. **OutputFormattingService** - Formats data using templates with JSON Schema validation
4. **TemplateRegistryService** - Built-in visualization templates

### What's Missing

1. **Backend does not return structured_data** - `FormattedResponse` has no `structured_data` field
2. **Schema not passed to LLM** - `response_format` parameter not used
3. **Frontend not wired** - `formatStructuredOutput()` is a placeholder
4. **No end-to-end flow** - Components exist but are isolated

**Current (broken) flow:**
```
Use Case Config (output_schema defined)
  → LLM Response (text only)
  → ResponseFormatter.validate_output() ← validates but discards
  → FormattedResponse ← no structured_data field
  → Frontend ← receives only text, can't render visualizations
```

**What needs to be decided?** How to complete the structured output pipeline to enable visualization rendering.

---

## Decision

**What did we decide?**

Complete the structured output pipeline by:

1. Adding `structured_data` field to `FormattedResponse`
2. Extracting and validating structured data in ResponseFormatter
3. Passing `response_format` to LLM API (optional, model-dependent)
4. Wiring frontend to render visualizations from `structured_data`

### 1. Backend Schema Change

```python
# src/orchestrator/app/schemas/response.py

class FormattedResponse(BaseModel):
    response: str
    sources: list[SourceMetadata]
    confidence: float
    metrics: ConsolidatedMetrics
    suggested_actions: dict
    request_id: str
    cache_stats: dict | None = None

    # NEW FIELD
    structured_data: dict[str, Any] | None = Field(
        default=None,
        description="Parsed structured output when output_contract.format is json/yaml/structured"
    )
```

### 2. Structured Data Extraction

```python
# src/orchestrator/app/orchestrator/response_formatter.py

async def process(self, response_text: str, output_contract: OutputContractConfig | None, ...) -> FormattedResponse:
    structured_data = None

    if output_contract and output_contract.format in [OutputFormat.JSON, OutputFormat.YAML, OutputFormat.STRUCTURED]:
        try:
            # Parse response
            if output_contract.format == OutputFormat.YAML:
                structured_data = yaml.safe_load(response_text)
            else:
                structured_data = json.loads(response_text)

            # Validate against schema
            if output_contract.output_schema:
                validate(instance=structured_data, schema=output_contract.output_schema)

        except (json.JSONDecodeError, yaml.YAMLError, ValidationError) as e:
            if output_contract.validation_mode == ValidationMode.STRICT:
                raise HTTPException(status_code=422, detail=f"Output validation failed: {e}")
            else:
                logger.warning(f"Structured output parsing failed: {e}")
                structured_data = None

    return FormattedResponse(
        response=response_text,
        structured_data=structured_data,  # NEW
        ...
    )
```

### 3. LLM Response Format (Optional Enhancement)

```python
# src/orchestrator/app/orchestrator/llm_client.py

async def make_completion_request(self, messages, model, output_contract=None, **kwargs):
    request_params = {"messages": messages, "model": model, **kwargs}

    # Add response_format for JSON/structured outputs (OpenAI-compatible)
    if output_contract and output_contract.format in [OutputFormat.JSON, OutputFormat.STRUCTURED]:
        if output_contract.output_schema:
            request_params["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "schema": output_contract.output_schema,
                    "strict": output_contract.validation_mode == ValidationMode.STRICT
                }
            }
        else:
            request_params["response_format"] = {"type": "json_object"}

    return await self._make_request(request_params)
```

### 4. Frontend Integration

```typescript
// src/frontend-angular/src/app/api/models/use-case.models.ts
export interface ExecutionResponse {
  response: string;
  sources: SourceMetadata[];
  metrics: ConsolidatedMetrics;
  request_id: string;
  // ... existing fields ...

  // NEW
  structured_data?: Record<string, unknown>;
}

// src/frontend-angular/src/app/pages/use-case-execution/use-case-execution.component.ts
private async processExecutionResult(result: ExecutionResponse): Promise<void> {
  this.executionResult = result;

  // NEW: Process structured output
  if (result.structured_data && this.useCaseConfig?.output_contract?.template_id) {
    const template = this.templateRegistry.getTemplate(
      this.useCaseConfig.output_contract.template_id
    );

    if (template) {
      this.formattedOutput = await this.outputFormattingService.formatResponse(
        { answer: result.response, structured_data: result.structured_data },
        template
      );
      this.hasStructuredOutput = true;
    }
  }
}
```

---

## Alternatives Considered

### Option 1: Client-Side Parsing Only

**Description:** Backend returns raw text; frontend parses and validates JSON.

**Pros:**
- Simpler backend changes
- Frontend already has Ajv

**Cons:**
- Duplicated validation logic
- No server-side schema enforcement
- Streaming responses can't be validated until complete

**Why Rejected:** Validation belongs on the server for consistency and security.

### Option 2: Separate Structured Output Endpoint

**Description:** Create a new `/execute-structured` endpoint that always returns structured data.

**Pros:**
- Clear separation of concerns
- No changes to existing endpoint

**Cons:**
- API fragmentation
- Duplicated execution logic
- Client must know which endpoint to call

**Why Rejected:** Adds unnecessary complexity; better to extend existing endpoint.

### Option 3: Always Return Both Text and Structured

**Description:** Parse response as JSON when possible, always include both fields.

**Pros:**
- Maximum flexibility
- Graceful degradation

**Cons:**
- Unnecessary parsing overhead for text-only use cases
- Confusing API semantics

**Why Rejected:** Should only attempt parsing when output_contract specifies structured format.

---

## Consequences

### Positive Consequences

- Existing visualizer components (table, chart, gauge, timeline) become functional
- P3-F5 Output Formatting Engine investment is realized
- AI Ops developers can build rich, interactive use case outputs
- Consistent visualization across all structured use cases

### Negative Consequences

- Additional processing overhead for structured outputs
- LLM must produce valid JSON/YAML (may require prompt engineering)
- Streaming responses need special handling for validation

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| LLM produces invalid JSON | Medium | Use `response_format` with compatible models; best_effort mode |
| Performance overhead | Low | Only parse when output_contract.format is structured |
| Breaking existing clients | Low | `structured_data` is optional field; existing clients ignore it |
| Schema mismatch with template | Medium | UI validation that schema matches template expectations |

---

## Implementation Notes

**Files affected:**
- `src/orchestrator/app/schemas/response.py` - Add structured_data field
- `src/orchestrator/app/orchestrator/response_formatter.py` - Extract structured data
- `src/orchestrator/app/orchestrator/llm_client.py` - Add response_format (optional)
- `src/frontend-angular/src/app/api/models/use-case.models.ts` - Add TypeScript type
- `src/frontend-angular/src/app/pages/use-case-execution/use-case-execution.component.ts` - Wire rendering

**Migration steps:**
- None required (additive change)
- Existing use cases continue to work unchanged

**Dependencies:**
- `jsonschema` (already in project for validation)
- `pyyaml` (already in project for YAML parsing)

**Testing strategy:**
- Unit tests for response formatter structured data extraction
- Integration tests for end-to-end structured output flow
- E2E tests for visualization rendering

---

## References

- Implementation Plan: `docs/development/plans/features/active/USE_CASE_AUTHORING_COMPLETE_SPEC.md`
- Discovery: `docs/development/analysis/AI_OPS_USE_CASE_AND_STRUCTURED_OUTPUT_DISCOVERY.md`
- P3-F5 Spec: `docs/development/plans/features/completed/P3-F5_OUTPUT_FORMATTING_ENGINE_SPEC.md`
- Structured Output Guide: `docs/user-guides/STRUCTURED_OUTPUT_GUIDE.md`
- ADR-018: Use Case Owned Architecture

---

## Amendment: Schema-Template Compatibility Validation (2026-02-05)

### Context

Phase 4bis review identified that authors can select a visualization template and define an output schema that are incompatible. For example, selecting "Score + Table + Timeline" (expects `$.confidence`, `$.iocs`, `$.timeline`) but defining a schema with `$.results` and `$.score`. The visualization silently fails at runtime.

Additionally, authors iterating on use cases must manually compare LLM output against their schema — there is no feedback loop from execution results back to schema refinement.

### Amendment 1: Schema-Template Compatibility Validation

Each template's `layout.sections` contains `data_path` expressions (JSONPath). The wizard validates that the user's output schema contains properties matching these paths.

**Validation logic:**
1. Extract root key from each template section's `data_path` (e.g., `"$.iocs"` -> `"iocs"`)
2. Check if the user's schema has a `properties` entry with that key
3. Optionally check type compatibility (array vs object vs primitive)

**Status levels:**

| Status | Meaning | UI | Blocks Save? |
|------|------|------|------|
| Full match | All template data_paths found in schema | Green check | No |
| Partial match | Some paths missing | Yellow warning listing missing paths | No |
| No match | No template paths found in schema | Red warning | No (template is optional) |
| No template | No template selected | Hidden | N/A |

**Auto-populate on template selection:**
- If schema editor is empty and author selects a template: auto-populate schema from `template.data_schema`, show toast "Schema populated from template. Customize as needed."
- If schema already has content: prompt "Replace schema with template schema?" with Yes/No

### Amendment 2: Schema Feedback Loop ("Refine from Output")

Add a "Refine Schema" action on the use case execution results page:

1. After execution, if `structured_data` is present, show button: **"Generate Schema from This Output"**
2. Opens a dialog showing:
   - Left panel: current output schema (from use case config)
   - Right panel: schema inferred from actual `structured_data`
   - Differences highlighted
3. Author actions: "Replace with inferred", "Merge (add missing fields)", or "Cancel"
4. If accepted, navigates to wizard in edit mode with updated schema pre-filled

**Implementation:** Reuse the existing schema inference logic from `SchemaEditorComponent.generateSchemaFromExample()`, extracted to a shared utility service.

### Files Changed (Amendment)

| File | Change |
|------|--------|
| Wizard Step 3 output configuration area | Add compatibility status display below template selector |
| Schema editor component area | Auto-populate schema on template selection |
| Execution page component | Add "Generate Schema from This Output" button and dialog |
| New: shared schema inference utility | Extract `generateSchemaFromExample()` logic for reuse |

---

## Status Updates

### 2026-02-04 - Proposed

**Changed By:** AI Operations Platform Team
**Reason:** Initial proposal to complete the structured output pipeline identified in discovery analysis.

### 2026-02-05 - Amended

**Changed By:** AI Operations Platform Team
**Reason:** Phase 4bis review added schema-template compatibility validation (non-blocking warnings in wizard) and schema feedback loop (refine schema from execution output). These ensure the pipeline is not just end-to-end but also iteratively improvable.

---

**Template Version:** 1.0
**Based On:** Michael Nygard's ADR pattern
