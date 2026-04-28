# AI Operations Use Case & Structured Output: Question and Discovery

**Purpose:** Capture the product question and the initial code/doc analysis so the work can be tackled in a separate thread (e.g. with Opus). Single source of truth for "what we want" vs "what exists."

**Date:** 2025-02-04

---

## 1. The Question (Product Intent)

The application should allow an **AI Ops developer** to create a use case that:

1. **Accepts parameters as user input**
   - Parameters should be **validatable** (e.g. by type and/or by list of values).
   - Types and/or possible values (List Of Values) should be configurable.

2. **Merges parameters into the AI Ops user prompt template**
   - The prompt does not have to be a template—it could be plain instructions or a question, depending on what the AI Ops developer needs.
   - Parameters are then **merged with the User Prompt Template**, and that is **combined with the other prompts** (system, developer, etc.).

3. **Specifies a Structured Output object for the LLM response**
   - The AI Ops developer can define a structured output shape for the LLM response.
   - This should include **field validation** (e.g. JSON Schema).

The question posed: **Is there documentation or completed code that implements this functionality?**

---

## 2. Summary of Discovery

| Capability | Implemented? | Notes |
|------------|--------------|--------|
| Parameters as user input (type, LOV) | **Yes** | `input_fields` + `options`; backend enforces required; frontend builds form. |
| Input validation (min/max length, pattern) | **Frontend only** | UI validators from `field.validation`; backend does not define or enforce `validation` in schema. |
| **Parameters merged into a user prompt template** | **No** | Parameters are only concatenated as `"key: value"` and used as the single `query`; no editable user prompt template. |
| System + developer + context + history + query combined | **Yes** | AssemblePrompt uses a fixed template with one `query` slot. |
| Structured output schema + validation (backend) | **Yes** | `OutputContractConfig` + response formatter validate LLM output against `output_schema`. |
| Structured output returned to client / rendered in execution UI | **No** | No `structured_data` in API response; execution page does not load template or call formatter. |

**Bottom line:** Parameter collection and LOV work; "user prompt template with parameter placeholders" does not exist (and was explicitly removed). Structured output is specified and validated on the backend but is not returned or rendered in the use-case execution flow.

---

## 3. Detailed Findings

### 3.1 Parameters as User Input (Validatable, Type, LOV)

**Implemented:**

- **Backend** (`src/orchestrator/app/schemas/use_case_config.py`): `InputFieldConfig` has `name`, `type` (text, textarea, select, number, checkbox, date), `label`, `description`, `required`, `placeholder`, `default_value`, and `options` (list of `{value, label}`) for select = List Of Values. Select fields must have at least one option.
- **Execution** (`src/orchestrator/app/routers/use_cases.py` ~428–436): Validates that all required input fields are present; returns 400 if missing.
- **Frontend** (`src/frontend-angular/src/app/api/models/use-case.models.ts` ~232–266, `use-case-execution.component.ts` ~205–230): `InputField` has optional `validation` (`min_length`, `max_length`, `min_value`, `max_value`, `pattern`). The execution form applies Angular validators from `field.validation`. Backend does not define or enforce this `validation` object in the schema (config uses `extra: "allow"` so it can be stored).

**Doc caveat:** `docs/api/use-case-execution.md` "Dynamic Input Handling" describes `ui_config.input_sections` and `validation_pattern`; the code uses `config_json.input_fields` and (on the frontend) `validation`. Doc and code are not fully aligned.

---

### 3.2 Parameters Merged into a User Prompt Template

**Not implemented.**

- The "user" content sent to the LLM is **not** from a configurable user prompt template. In `src/orchestrator/app/routers/use_cases.py` (~438–445):
  - For each `execution.inputs`: build `"field_name: value"`.
  - `query_text = "\n".join(query_parts)`.
- That string is passed as the single **query** variable. In `src/orchestrator/app/orchestrator/steps/assemble_prompt.py`, the assembly template is **fixed**: placeholders are `system_prompt`, `developer_prompt`, `context`, `history`, and **`query`**. The `query` slot is always this concatenated key:value text.
- There is **no** configurable "user prompt template" (e.g. "Analyze {{incident_details}} for time range {{time_range}}") that the developer can edit. Session note: `docs/development/sessions/2025-10-19-p3-multi-role-prompts.md` — **"Removed unused `user_prompt_template` field"**.
- `UseCasePromptSet` (`src/orchestrator/app/schemas/use_case_management.py` ~34–49) has `system_prompt`, `developer_prompt`, `fewshots`, and `variables` (list of variable names). In the use-case execution path, `variables` is not used to substitute into a **user** template; AssemblePrompt does not load a per–use-case "user message template" filled with input field values.

So: parameters are **not** merged into a developer-defined user prompt template; they are only turned into a single "query" string in a fixed format.

---

### 3.3 Prompt Flexibility and Combination with Other Prompts

**Partially as intended:**

- System and developer prompts can be "just instructions" or a question—they are freeform. No requirement that they be templates.
- **Combination is implemented:** system prompt, developer prompt, context (retrieved docs), history, and the single "query" (concatenated inputs) are assembled in AssemblePrompt and sent to the LLM. The gap is that the "user" part is not a custom template; it is the fixed key:value format above.

---

### 3.4 Structured Output Object with Field Validation

**Backend: implemented for validation; not exposed in the API.**

- **Config** (`src/orchestrator/app/schemas/use_case_config.py` ~313–331): `OutputContractConfig` has `format` (text | json | yaml | structured), `output_schema` (JSON Schema), and `validation_mode` (best_effort | strict). So the developer **can** specify a structured output schema and validation mode.
- **Validation** (`src/orchestrator/app/orchestrator/response_formatter.py`): The formatter validates the LLM response against `output_contract` (format + schema); for JSON/YAML/structured it can use `output_schema` and enforce strict vs best-effort.
- **Gap:** `FormattedResponse` (`src/orchestrator/app/schemas/response.py`) has **no** `structured_data` field. The validated/parsed structured payload is never returned to the client. The execution API returns `response` (text), `sources`, `metrics`, etc., but not the structured object.
- **Frontend:** The execution page does not load an output template when `output_format === 'structured'`, does not call the formatter with backend data, and `ExecutionResponse` (`src/frontend-angular/src/app/api/models/use-case.models.ts`) has no `structured_data`. So end-to-end "structured output in the execution UI" is not implemented.

**Docs:** `docs/user-guides/STRUCTURED_OUTPUT_GUIDE.md` and `STRUCTURED_OUTPUT_QUICKSTART.md` describe the intended behavior; `docs/user-guides/use-case-validation.md` describes developer prompt and output_schema for JSON/structured. The **design** is documented; the **execution path** (backend returning `structured_data` + frontend rendering it) is not completed.

---

## 4. Key Code and Doc References

| Topic | Location |
|-------|----------|
| Input fields schema (backend) | `src/orchestrator/app/schemas/use_case_config.py` — `InputFieldConfig`, `InputFieldType`, `InputFieldOption` |
| Building query from inputs | `src/orchestrator/app/routers/use_cases.py` ~424–445 |
| Prompt assembly (fixed template, query slot) | `src/orchestrator/app/orchestrator/steps/assemble_prompt.py` — `_build_template_and_vars`, `run` |
| Use case prompt set (no user template) | `src/orchestrator/app/schemas/use_case_management.py` — `UseCasePromptSet` |
| Output contract (format, schema, validation) | `src/orchestrator/app/schemas/use_case_config.py` — `OutputContractConfig` |
| Response formatter (validates output) | `src/orchestrator/app/orchestrator/response_formatter.py` — `_validate_against_contract`, `process` |
| FormattedResponse (no structured_data) | `src/orchestrator/app/schemas/response.py` — `FormattedResponse` |
| Execution component (structured output TODOs) | `src/frontend-angular/src/app/pages/use-case-execution/use-case-execution.component.ts` — `loadOutputTemplate` ~L191, `formatStructuredOutput` ~L431 |
| Frontend ExecutionResponse type | `src/frontend-angular/src/app/api/models/use-case.models.ts` — `ExecutionResponse` |
| User prompt template removed | `docs/development/sessions/2025-10-19-p3-multi-role-prompts.md` |
| Structured output design | `docs/user-guides/STRUCTURED_OUTPUT_GUIDE.md`, `STRUCTURED_OUTPUT_QUICKSTART.md` |
| Use case validation (output_schema, developer prompt) | `docs/user-guides/use-case-validation.md` |
| Broader TODO list (Structured Output + others) | `docs/development/analysis/CODE_TODO_CONSOLIDATION_ANALYSIS.md` |

---

## 5. Implementation Plan

> **DETAILED SPEC CREATED:** A comprehensive implementation plan has been created based on this discovery.
>
> **See: [`docs/development/plans/features/active/USE_CASE_AUTHORING_COMPLETE_SPEC.md`](../plans/features/active/USE_CASE_AUTHORING_COMPLETE_SPEC.md)**

### Summary of Planned Work

| Phase | Feature | Priority | Est. Time |
|-------|---------|----------|-----------|
| 1 | **Input Fields Configuration** - Add builder to wizard | Critical | 4 days |
| 2 | **User Prompt Template** - `{{variable}}` placeholders | High | 5 days |
| 3 | **Structured Output Pipeline** - Return parsed data | High | 2.5 days |
| 4 | **Output Visualization** - Template selector | Medium | 2.5 days |
| 5 | Documentation & Polish | Medium | 3 days |

### Key Findings from Deep Analysis

1. **Wizard Gap Confirmed:** Step 4 (Configure) has no UI for input fields - every use case gets a hardcoded default "query" field
2. **Components Exist:** InputField models, DynamicForm components, and visualizers are implemented but not wired
3. **Pipeline Incomplete:** Backend validates structured output but discards it; frontend never receives `structured_data`

---

## 5.1 Original Workstreams (Reference)

1. **User prompt template with parameter merge**
   - Add a user-editable "user prompt template" (or "user message template") to the use case (e.g. in prompt set or config), with placeholders that map to input field names.
   - In execution: build the user message by substituting `execution.inputs` into this template (instead of concatenating `"key: value"`).
   - In AssemblePrompt: either keep a single `query` slot filled with this rendered user message, or introduce a distinct "user_message" built from the template. Ensure system/developer/context/history combination remains as today.

2. **Structured output end-to-end**
   - Backend: Add `structured_data` (e.g. optional dict) to `FormattedResponse`; in the pipeline, when `output_contract.format` is json/yaml/structured, parse the LLM response and set `structured_data` on the response.
   - Frontend: Add `structured_data?: unknown` to `ExecutionResponse`; after execution (standard and streaming), if present, call existing formatting/rendering (load template when `output_format === 'structured'`, call `formatStructuredOutput(result)`), and show the structured output section.

3. **Input validation parity (optional)**
   - Backend: Add an optional `validation` sub-object to `InputFieldConfig` (min_length, max_length, pattern, min_value, max_value) and validate execution inputs against it so server-side behavior matches the frontend.

4. **Docs**
   - Align `docs/api/use-case-execution.md` with actual `config_json.input_fields` and frontend `validation` shape.
   - Update or add a doc that explicitly states whether “user prompt template” is in scope and how it works once implemented.

---

## 6. Related Documents

- **CODE_TODO_CONSOLIDATION_ANALYSIS.md** — Full list of TODOs (Structured Output, document viewing, auth, etc.) and importance.
- **ADR-018** — Use Case Owned Architecture (prompts owned by use case).
- **ADR-044** — Use cases as bounded refinement spaces (input_fields vs conversational).
- **PUBLICATION_AUDIT_PLAN.md** — Broader audit plan; can reference this discovery for AI Ops / use-case / structured output scope.

This document is the starting point for “attacking head on” the AI Ops use-case and structured output behavior in a separate thread.
