# Code TODO Consolidation and Importance Analysis

**Purpose:** Single reference for all TODOs in production/source code, grouped by importance so you can decide what is already done, what is still needed, and what to prioritize.

**Date:** 2025-02-04

---

## Summary

- **High:** Gaps that affect core flows (use-case execution, structured output, auth, documents).
- **Medium:** Feature completeness (documents, templates, permissions, real metrics).
- **Low:** Tech debt, placeholders, deferred work.

**Notable finding:** Structured Output is **not** implemented end-to-end for use-case execution. The UI (Structured Output Renderer, template docs) and `OutputFormattingService` exist, but the execution page never loads templates or formats structured data because the backend does not return `structured_data` and the frontend never calls the formatter after execution.

---

## High importance (core flows / promised behavior)

### 1. Structured Output in use-case execution (frontend + backend)

**Status:** Not implemented. Docs and UI suggest it exists; execution path does not use it.

| Location | TODO / gap | What’s missing |
|----------|-------------|----------------|
| `src/frontend-angular/.../use-case-execution.component.ts` ~L191 | "Load template from backend when output format is 'structured'" | `loadOutputTemplate()` is a no-op; no template service call when `output_format === 'structured'`. |
| Same file ~L434 | "Implement when backend returns structured_data" | `formatStructuredOutput()` is never called after `executeStandard()` or streaming `complete`; and there is no `structured_data` to format. |
| Same file | (implicit) | After `this.executionResult = result` (and streaming `response.data`), there is no `await this.formatStructuredOutput(result)`. So even with backend data later, frontend would not render it. |
| `src/frontend-angular/.../use-case.models.ts` | (type gap) | `ExecutionResponse` has no `structured_data?: unknown`. |
| Backend `src/orchestrator/app/schemas/response.py` | (schema gap) | `FormattedResponse` has no `structured_data` field. |
| Backend pipeline | (behavior gap) | No step parses LLM JSON into a structured payload or attaches it to the response. |

**What exists:** `StructuredOutputRendererComponent`, `OutputFormattingService`, `output_format: 'text' | 'json' | 'structured'` in config, STRUCTURED_OUTPUT_GUIDE.md. So the “feature” is documented and partially built but not wired in the execution flow.

**Recommendation:** Treat as a single feature: add `structured_data` to backend response and pipeline, add to frontend `ExecutionResponse`, load template when `output_format === 'structured'`, and call `formatStructuredOutput(result)` after non-streaming and streaming complete.

---

### 2. Session service encryption (frontend)

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/frontend-angular/.../session.service.ts` | 372, 393 | "Implement encryption if enabled" / "Implement decryption if enabled" | Session storage read/write; if “encryption enabled” is a real product requirement, this is a security gap. |

**Recommendation:** Confirm whether encryption is required; if yes, implement or document as known limitation.

---

### 3. Document viewing (frontend)

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/frontend-angular/.../document-processing.component.ts` | 771 | "Implement document viewing" | User-facing. |
| `src/frontend-angular/.../document-processing-new.component.ts` | 635 | "Implement document viewing" | Same. |

**Recommendation:** Implement or remove duplicate component and centralize “document viewing” behind one implementation.

---

### 4. Source citation – document actions (frontend)

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/frontend-angular/.../source-citation.component.ts` | 196, 201 | "Navigate to document viewer or show document details" / "Implement document download functionality" | Tied to document viewing and download. |

**Recommendation:** Resolve with document-viewing work above.

---

### 5. Auth and permissions (backend + frontend)

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/shared/auth/router.py` | 338 | "Count active sessions" | Session list returns `session_count: 0`. |
| `src/frontend-angular/.../user-create-dialog.component.ts` | 93 | "Add username uniqueness check API call" | Data integrity / UX. |
| `src/frontend-angular/.../use-case-list.component.ts` | 318, 323, 329 | "Check user permissions based on useCase state/ownership" (and similar) | Permissions for run/edit/delete. |
| `src/frontend-angular/.../collection.service.ts` | 54 | "Fix admin endpoint authentication issue" | Blocks admin collection usage if hit. |
| `src/corpus_svc/app/routers/collections.py` | 458, 498 | "Implement auth" on some endpoints | Permissions not enforced. |

**Recommendation:** Prioritize session count and use-case permissions; then admin/auth fixes for collections and user create.

---

## Medium importance (feature completeness)

### 6. Template editor save (frontend)

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/frontend-angular/.../template-editor.component.ts` | 122 | "Call use case service to save template" | Template edits may not persist. |

---

### 7. Chunking / documents (frontend)

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/frontend-angular/.../chunking-analysis.component.ts` | 767, 776 | "Implement save preset dialog" / "Apply configuration and upload document" | Chunking UX incomplete. |

---

### 8. Backend execution / integrations

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/orchestrator/app/services/use_case_testing_service.py` | 100 | "Orchestrator.process_request() doesn't exist - needs refactoring to use UseCaseRunner pipeline" | Test execution path may be outdated. |
| `src/corpus_svc/app/routers/test_suites.py` | 247, 270 | "Implement actual execution logic with retrieval service integration" / "Implement actual execution" | Test suite execution stubbed. |
| `src/corpus_svc/app/services/preflight_service.py` | 277 | "Compute retrieval metrics if test_suite_id provided" | Metrics for test suite. |
| `src/corpus_svc/app/routers/collections.py` | 396 | "Delete corresponding Qdrant collection" | Collection delete may leave Qdrant state out of sync. |

---

### 9. Real metrics / observability (backend + frontend)

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/orchestrator/app/routers/websocket.py` | 327–335 | "track real API latency" / "track real requests/sec" / "track real error rate" / "track real disk I/O" / "track real network I/O" / "track real queue" | WebSocket health/metrics are placeholders. |
| `src/frontend-angular/.../metrics.service.ts` | 180 | "Track errors when available" | success_rate hardcoded 1.0. |
| `src/frontend-angular/.../metrics-dashboard.component.ts` | 210 | "Get from parent component" | Test query is hardcoded. |

---

### 10. Inference gateway streaming

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/inference-gateway/app/routers/responses.py` | 146 | "Implement streaming for responses API" | Non-streaming only for that API. |

---

## Lower importance (tech debt, placeholders, deferred)

### 11. Backend tech debt / refactors

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/orchestrator/app/orchestrator/response_formatter.py` | 845 | "Convert format_response to async when Orchestrator is converted (Phase 5)" | Async migration. |
| `src/orchestrator/app/services/conversation_cache.py` | 60 | "Replace with tiktoken for accurate counting" | Token counting. |
| `src/orchestrator/app/services/tool_registration_service.py` | 64 | "Replace with Redis for production" | In-memory session store. |
| `src/orchestrator/app/orchestrator/steps/README.md` | 19, 25, 31, 41, 52, 106 | Steps "Requiring Implementation" / schema compatibility / extract logic | Pipeline step stubs. |

---

### 12. Frontend UX / minor behavior

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/frontend-angular/.../table-visualizer.component.ts` | 137 | "Show snackbar notification" | Small UX. |
| `src/frontend-angular/.../collection-list.component.ts` | 329 | "Create stats dialog" | Currently `alert(JSON.stringify(stats))`. |
| `src/frontend-angular/.../use-case-wizard.component.ts` | 133 | "Fetch from backend config" | `systemEmbeddingModel` hardcoded. |

---

### 13. Graph / threat intel (frontend)

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/frontend-angular/.../graph-visualization.service.ts` | 90, 105, 120, 213 | "Implement based on threat intelligence data structure" / "IOC" / "MITRE ATT&CK" / "Neo4j driver results format" | Visualization backends not implemented. |

---

### 14. Tests and load tests

| File | Line | TODO | Notes |
|------|------|------|------|
| `src/frontend-angular/.../structured-output-renderer.component.spec.ts` | 74 | "Test is currently skipped due to ExpressionChangedAfterItHasBeenCheckedError" | Fix or accept. |
| `src/orchestrator/tests/unit/routers/test_tools_registration.py` | 103 | "Refactor tests to use proper FastAPI testing patterns" | Test quality. |
| `tests/load/load_test.py` | 154 | "Update when orchestrator proxy endpoint is implemented (P3-T5)" | Load test endpoint. |

---

## Reference: TODO locations (production/source code only)

Excluding docs, session logs, and templates; only files that affect runtime behavior.

| File | Line | Snippet |
|------|------|--------|
| `src/frontend-angular/.../use-case-execution.component.ts` | 191 | Load template when output format is 'structured' |
| `src/frontend-angular/.../use-case-execution.component.ts` | 434 | Implement when backend returns structured_data |
| `src/frontend-angular/.../session.service.ts` | 372, 393 | Encryption/decryption if enabled |
| `src/frontend-angular/.../template-editor.component.ts` | 122 | Call use case service to save template |
| `src/frontend-angular/.../document-processing.component.ts` | 771 | Implement document viewing |
| `src/frontend-angular/.../document-processing-new.component.ts` | 635 | Implement document viewing |
| `src/frontend-angular/.../table-visualizer.component.ts` | 137 | Show snackbar notification |
| `src/frontend-angular/.../structured-output-renderer.component.spec.ts` | 74 | Skipped test (ExpressionChanged...) |
| `src/frontend-angular/.../source-citation.component.ts` | 196, 201 | Document viewer navigation; document download |
| `src/frontend-angular/.../metrics-dashboard.component.ts` | 210 | Get query from parent component |
| `src/frontend-angular/.../user-create-dialog.component.ts` | 93 | Username uniqueness check API |
| `src/frontend-angular/.../use-case-list.component.ts` | 318, 323, 329 | Check user permissions |
| `src/frontend-angular/.../chunking-analysis.component.ts` | 767, 776 | Save preset dialog; apply config and upload |
| `src/frontend-angular/.../collection-list.component.ts` | 329 | Create stats dialog |
| `src/frontend-angular/.../collection.service.ts` | 54 | Fix admin endpoint authentication |
| `src/frontend-angular/.../use-case-wizard.component.ts` | 133 | Fetch systemEmbeddingModel from backend |
| `src/frontend-angular/.../metrics.service.ts` | 180 | Track errors when available |
| `src/frontend-angular/.../graph-visualization.service.ts` | 90, 105, 120, 213 | Implement threat intel / IOC / MITRE / Neo4j |
| `src/orchestrator/app/routers/websocket.py` | 327–335 | Track real latency, throughput, error rate, I/O, queue |
| `src/orchestrator/app/orchestrator/response_formatter.py` | 845 | Convert format_response to async (Phase 5) |
| `src/orchestrator/app/services/conversation_cache.py` | 60 | Replace with tiktoken |
| `src/orchestrator/app/services/use_case_testing_service.py` | 100 | Refactor to UseCaseRunner pipeline |
| `src/orchestrator/app/services/tool_registration_service.py` | 64 | Replace with Redis for production |
| `src/shared/auth/router.py` | 338 | Count active sessions |
| `src/corpus_svc/.../preflight_service.py` | 277 | Compute retrieval metrics if test_suite_id |
| `src/corpus_svc/app/routers/collections.py` | 396, 458, 498 | Delete Qdrant collection; implement auth |
| `src/corpus_svc/app/routers/test_suites.py` | 247, 270 | Actual execution logic |
| `src/inference-gateway/app/routers/responses.py` | 146 | Implement streaming for responses API |
| `tests/load/load_test.py` | 154 | Update when orchestrator proxy implemented |
| `src/orchestrator/tests/.../test_tools_registration.py` | 103 | Refactor to FastAPI testing patterns |

---

## Next steps

1. **Structured Output:** Confirm product expectation (P3-F5 or sooner). If in scope, implement backend `structured_data`, frontend type + template load + `formatStructuredOutput()` call after execution (standard and streaming).
2. **Document viewing:** Decide single entry point (which component), then implement and remove duplicate TODOs.
3. **Auth/permissions:** Implement session count, use-case permission checks, and fix collection admin auth; add username uniqueness where required.
4. **Mark completed:** For any TODOs that are already done, remove the comment or replace with a short note and update this doc.
5. **Defer explicitly:** For low-priority items, consider moving them to a backlog doc and removing inline TODOs to reduce noise.

If you tell me which area you consider “already done” (e.g. structured output vs document viewing), I can suggest concrete code changes and checklist updates for that area.
