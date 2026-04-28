# ADR-068: Portable Visualization Specification (Vega-Lite)

**Status:** Accepted
**Date:** 2026-02-05
**Deciders:** AI Operations Platform Team
**Tags:** visualization, vega-lite, api, portable, structured-output, mcp

---

## Context

**What is the issue we're addressing?**

The platform returns `structured_data` in API responses (per ADR-063), but visualization is a frontend-only concern. The `TemplateRegistryService` renders structured data using Angular components (tables, charts, gauges, timelines). This means:

1. **API consumers (scripts, SOAR, Jupyter, external dashboards) cannot render visualizations** — they receive raw JSON and must build their own rendering logic
2. **Visualization knowledge is locked in the frontend** — template layout definitions, component configs, and data extraction logic exist only in TypeScript
3. **No portability** — the same structured data rendered beautifully in the browser UI is opaque JSON for a Python script

Since the platform is primarily consumed through API calls, this is a significant gap. API consumers who want visualizations must reverse-engineer the template system or build their own.

### Industry Standards Evaluated

| Standard | Strengths | Weaknesses |
|---|---|---|
| **Vega-Lite** | Declarative JSON grammar; renderers in Python (altair), JS (vega-embed), R, Jupyter; well-documented schema | Weaker for tables and card layouts |
| **Adaptive Cards** | Cross-platform (Teams, Outlook, Copilot); good for tables and forms | Narrower ecosystem; Microsoft-centric |
| **MCP Apps** | Official MCP extension for tool result rendering; supports rich interactive UIs | Iframe-based (HTML bundles), not declarative JSON |

**What needs to be decided?** Whether and how to include a portable visualization specification in API responses.

---

## Decision

**What did we decide?**

Add an optional `visualization_spec` field to the execution API response using **Vega-Lite** for chart/gauge/timeline visualizations and a **lightweight table spec** for tabular data. This creates a three-layer visualization model:

### Three-Layer Model

| Layer | Format | Consumers | When Present |
|---|---|---|---|
| `structured_data` | Raw JSON | Everyone (scripts, SOAR, notebooks, UIs) | Always (when output format is json/yaml/structured) |
| `visualization_spec` | Vega-Lite + table spec | Notebooks (altair), dashboards, platform UI | When template_id is configured and structured_data is available |
| MCP Apps UI | HTML bundle in sandboxed iframe | MCP clients (Claude, ChatGPT, VS Code) | Future — when platform acts as MCP server |

### API Response Schema

```python
class VisualizationSection(BaseModel):
    """One section of a visualization layout."""
    section_id: str
    title: str
    type: Literal["vega-lite", "table"]
    width: Literal["full", "half", "third", "two-thirds"] = "full"
    vega_lite_spec: dict[str, Any] | None = None
    table_spec: TableSpec | None = None


class TableSpec(BaseModel):
    """Portable table specification."""
    columns: list[TableColumn]
    data: list[dict[str, Any]]
    sortable: bool = True
    filterable: bool = False
    export_formats: list[str] = []


class TableColumn(BaseModel):
    """Column definition for portable tables."""
    field: str
    header: str
    sortable: bool = True
    width: str | None = None


class VisualizationSpec(BaseModel):
    """Top-level portable visualization specification."""
    version: str = "1.0"
    layout: Literal["single", "grid", "tabs"] = "grid"
    sections: list[VisualizationSection]
```

The `FormattedResponse` gains:

```python
visualization_spec: VisualizationSpec | None = Field(
    default=None,
    description="Portable visualization spec (Vega-Lite + table). "
                "Present when output_contract has template_id and "
                "structured_data is available."
)
```

### Generation Pipeline

A new `VisualizationSpecGenerator` backend service translates template + data into a portable spec:

```
OutputFormatTemplate (layout, sections with data_paths and component configs)
  + structured_data (actual execution result)
  = VisualizationSpec (self-contained, portable)
```

Component type mapping:

| Template Component | Spec Type | Output |
|---|---|---|
| `gauge` | `vega-lite` | Arc/radial mark with embedded data point |
| `chart` (bar, line, pie) | `vega-lite` | Corresponding Vega-Lite mark with embedded data array |
| `timeline` | `vega-lite` | Temporal point/tick mark with embedded event data |
| `table` | `table` | Column definitions + extracted data array |

All Vega-Lite specs are **self-contained** — data is embedded in the spec, not referenced via URL. This ensures specs can be rendered offline without additional API calls.

### Consumer Examples

**Python / altair:**
```python
response = client.execute_use_case(use_case_id, inputs)
if response.visualization_spec:
    for section in response.visualization_spec.sections:
        if section.type == "vega-lite":
            import altair as alt
            chart = alt.Chart.from_dict(section.vega_lite_spec)
            chart.save(f"{section.section_id}.png")
```

**Jupyter notebook:**
```python
import altair as alt
# Vega-Lite renders natively inline in Jupyter
alt.Chart.from_dict(section.vega_lite_spec)
```

### Frontend Integration

The platform's browser UI can either:
- Continue using its Angular visualizer components (no change needed — current approach)
- Render Vega-Lite specs directly via `vega-embed` or `ngx-vega` (future option for parity)

Both approaches are valid. Angular components provide tighter Material Design integration; direct Vega-Lite rendering provides exact parity with API consumers.

### MCP Server Compatibility (Future)

When the platform exposes use cases as MCP tools (future work stream per MCP Apps specification, January 2026):

- `visualization_spec` sections can generate MCP Apps HTML bundles
- A Vega-Lite spec can be rendered to an HTML page using `vega-embed` and served as a `ui://` resource
- The same template produces portable specs for API consumers AND interactive UIs for MCP clients
- This design explicitly supports this future direction without requiring MCP work now

---

## Alternatives Considered

### Option A: Adaptive Cards Instead of Vega-Lite

**Description:** Use Microsoft Adaptive Cards for the portable spec format.

**Pros:** Stronger for tables, forms, and card layouts; native rendering in Teams, Outlook, Copilot.
**Cons:** Narrower ecosystem outside Microsoft; weaker for data visualization (charts, gauges); requires Adaptive Cards SDK in consumers.
**Why Rejected:** Vega-Lite has broader ecosystem reach (Python, R, Jupyter, Observable) and is the stronger choice for data visualization, which is the primary use case for structured output rendering.

### Option B: No Portable Spec (Frontend Rendering Only)

**Description:** Keep visualization as a frontend-only concern; API returns only `structured_data`.

**Pros:** Simpler; no new backend service.
**Cons:** API consumers get no visualization help; Python scripts must build their own rendering; contradicts API-first principle.
**Why Rejected:** The platform's primary consumers are API callers — leaving them without visualization support undervalues the template system.

### Option C: Return Pre-Rendered Images (PNG/SVG)

**Description:** Backend renders visualizations to images and returns them as base64 in the response.

**Pros:** Universal rendering — any consumer can display an image.
**Cons:** Not interactive; large response payloads; server-side rendering requires headless browser or chart library; inflexible (consumer can't customize).
**Why Rejected:** Declarative specs are more flexible, smaller, and enable consumer-side customization.

---

## Consequences

### Positive Consequences

- API consumers can render visualizations using standard tools (altair, Jupyter, vega-embed)
- Python scripts get first-class visualization support without custom rendering code
- Template knowledge becomes portable — not locked in Angular components
- Foundation for MCP Server mode with MCP Apps UI rendering
- Vega-Lite specs are versioned, documented, and widely understood

### Negative Consequences

- New backend service (`VisualizationSpecGenerator`) to maintain
- Vega-Lite spec generation adds processing time to structured output responses
- Response payload increases when `visualization_spec` is present
- Vega-Lite is weaker for table rendering (hence the hybrid approach with `TableSpec`)

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Vega-Lite spec generation is complex | Medium | Start with simple marks (bar, arc, point); expand incrementally |
| Response payload size increases | Low | `visualization_spec` is optional; only present when template_id configured |
| Vega-Lite version drift | Low | Pin to Vega-Lite v6 schema; include `$schema` URL in specs |
| Consumers don't know Vega-Lite | Low | Document with examples; provide Python/JS helper snippets |

---

## Implementation Notes

### Files Changed

| File | Change |
|------|--------|
| `src/orchestrator/app/schemas/response.py` | Add `VisualizationSpec`, `VisualizationSection`, `TableSpec`, `TableColumn` models; add `visualization_spec` field to `FormattedResponse` |
| New: `src/orchestrator/app/services/visualization_spec_generator.py` | Service that translates template + structured_data into Vega-Lite specs |
| `src/orchestrator/app/orchestrator/response_formatter.py` | Call spec generator when template_id is present and structured_data is available |
| Frontend TypeScript models | Add `VisualizationSpec` interface to `ExecutionResponse` |

### Dependencies

- No new Python packages required for spec generation (Vega-Lite specs are plain JSON dicts)
- Consumers need `altair` (Python) or `vega-embed` (JavaScript) to render — these are consumer-side dependencies, not platform dependencies

---

## References

- Vega-Lite specification: https://vega.github.io/vega-lite/
- Vega-Lite JSON Schema: https://vega.github.io/schema/vega-lite/v6.json
- altair (Python): https://altair-viz.github.io/
- MCP Apps specification (January 2026): https://modelcontextprotocol.io/docs/extensions/apps
- ADR-063: Structured Output End-to-End Pipeline
- ADR-066: Domain-Neutral Visualization Template Architecture

---

## Status Updates

### 2026-02-05 - Accepted

**Changed By:** AI Operations Platform Team
**Reason:** Phase 4bis review identified that API consumers (the majority of platform users) receive no visualization support. Vega-Lite provides a portable, standards-based format that makes structured output renderable across Python, Jupyter, JavaScript, and future MCP clients.

---

**Template Version:** 1.0
**Based On:** Michael Nygard's ADR pattern
