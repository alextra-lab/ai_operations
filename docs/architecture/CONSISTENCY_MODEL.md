# Consistency Model: Stochastic Core, Deterministic Shell

**Status**: Active Pattern
**Date**: October 21, 2025
**Related**: [ADR-023](../development/adrs/ADR-023-Sampling-Presets-and-Guardrails.md), [GLOSSARY.md](../user-guides/GLOSSARY.md)

---

## Executive Summary

**The Problem**: LLMs are inherently stochastic (probabilistic). They cannot guarantee byte-identical outputs.

**The Solution**: Wrap the stochastic LLM in a **deterministic shell** of validators, policies, and contracts. The LLM may vary; the *system* produces reliable, auditable, spec-conformant results.

**Key Insight**: Don't fight the stochasticity—constrain it with architecture.

---

## Understanding Stochasticity

### What "Stochastic" Means

**Stochastic** = governed by probabilities, not fixed rules.

A stochastic system's output is drawn from a **probability distribution** `P(X)`. Repeated trials with identical inputs produce different samples `x ~ P(X)`.

**Contrast**: A **deterministic** system always maps the same input → same output.

### Why LLMs Are Stochastic

Even with identical prompts, an LLM generates each token by **sampling** from:

```
P(next_token | context)
```

**Variance sources**:
1. **Sampling algorithms**: Temperature, top-p, top-k shape the distribution but don't eliminate it
2. **Implementation details**: GPU kernels, parallelism, floating-point precision
3. **Model updates**: Different versions/checkpoints produce different distributions

**Bottom line**: At `temperature=0`, outputs are *more consistent*, not deterministic.

---

## Architectural Pattern: Stochastic Core + Deterministic Shell

```
┌─────────────────────────────────────────────────────┐
│  DETERMINISTIC SHELL (Your Control Surface)         │
│  ┌────────────────────────────────────────────┐    │
│  │ 1. Input Validation (LLM-Guard)            │    │
│  │ 2. Tool Allowlist Enforcement              │    │
│  │ 3. Structured Contracts (JSON Schema)      │    │
│  │                                             │    │
│  │    ┌──────────────────────────┐            │    │
│  │    │  STOCHASTIC CORE (LLM)   │            │    │
│  │    │  - May vary across runs  │            │    │
│  │    │  - Non-deterministic     │            │    │
│  │    └──────────────────────────┘            │    │
│  │                                             │    │
│  │ 4. Output Validation (Strict/BestEffort)   │    │
│  │ 5. Retry + Auto-Repair (Future: P4-F2)     │    │
│  │ 6. Audit Logging (Immutable Trail)         │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

### Key Principle

> **The LLM may vary. The shell enforces contracts.**

- **Stochastic core**: LLM decoding, sometimes retrieval ranking
- **Deterministic shell**: Validators, policy gates, state machines, idempotent actions

---

## What We Validate vs. What We Don't

### ✅ Validated (Enforced by Shell)

| Property | Validation Method | Failure Mode |
|----------|------------------|--------------|
| **Schema compliance** | JSON/YAML validator | Hard fail (strict) or log warning (best-effort) |
| **Required fields** | Pydantic models | HTTP 422 error |
| **Enum domains** | Type checking | Reject invalid values |
| **Tool allowlist** | Policy gate | Block execution, log violation |
| **Format structure** | Parser (json.loads, yaml.safe_load) | Parse error → retry or fail |
| **Token limits** | Max tokens parameter | Truncation at limit |
| **Idempotence** | Deduplication keys | Reject duplicate actions |

### ❌ Not Validated (Beyond Shell Capability)

| Property | Why We Can't Validate | Mitigation |
|----------|----------------------|------------|
| **Factual accuracy** | No ground truth in real-time | Human review, RAG source quality, retrieval confidence scores |
| **Semantic correctness** | No reliable automated reasoning checker | Prompt engineering, few-shot examples, analyst verification |
| **Completeness** | Unknown what "complete" means per query | Clear use case scoping, max_tokens tuning |
| **Absence of hallucination** | LLMs are generative by nature | Grounding via RAG, citation requirements, confidence thresholds |
| **Logical coherence** | Requires human judgment | Pattern library with tested prompts |

### 🎯 Targeted (Best-Effort, Not Guaranteed)

| Property | How We Target It | Measurable Proxy |
|----------|-----------------|------------------|
| **High consistency** | Strict preset (temp=0.15, top_p=0.90) | Retrieval Jaccard ≥0.80, embedding cosine sim ≥0.92 |
| **Relevant results** | Controlled RAG (k=6, time windows, filters) | Retrieval confidence scores |
| **Appropriate tone** | System prompts, few-shot examples | N/A (subjective) |

---

## Variance Control: Sampling Presets

We don't eliminate variance—we **bound** it through presets:

| Preset | Temperature | Top-P | Distribution Shape | Use Cases |
|--------|-------------|-------|-------------------|-----------|
| **Strict** | 0.15 | 0.90 | **Narrow** (high prob tokens only) | Threat triage, IOC extraction, classification |
| **Balanced** | 0.65 | 0.95 | **Moderate** (mix of likely tokens) | General Q&A, summarization, RAG |
| **Creative** | 0.85 | 0.97 | **Broad** (exploratory sampling) | Playbook drafting, scenario generation |

**Key insight**: `Strict` preset produces *high consistency* (functionally equivalent outputs), not determinism.

---

## Implementation: The Shell in Practice

### 1. Input Validation (LLM-Guard)

```python
# src/orchestrator/app/orchestrator/controller.py
sanitized, risk_score, modified, details = await self.validate_with_llm_guard(
    input_text=user_query,
    user_id=user_id,
    request_id=request_id
)
```

**Enforces**: No prompt injection, PII scanning, toxicity checks

---

### 2. Tool Allowlist Enforcement

```python
# src/orchestrator/app/orchestrator/controller.py
def _validate_tool_allowlist(self, use_case_config: UseCaseConfig):
    allowed_tools = set(use_case_config.tools_config.allowed_tools)
    for tool_name in requested_tools:
        if tool_name not in allowed_tools:
            raise ValueError(f"Tool {tool_name!r} not in allowlist")
```

**Enforces**: Only pre-approved tools can be invoked

---

### 3. Output Validation (Schema Contracts)

```python
# src/orchestrator/app/orchestrator/response_formatter.py
def validate_output(
    self, response_text: str, output_contract: OutputContractConfig
) -> tuple[str, dict[str, Any]]:
    if output_contract.format == OutputFormat.JSON:
        return self._validate_json_output(
            response_text, output_contract, validation_metadata
        )
```

**Enforces**: Outputs conform to JSON schema, required fields present

**Modes**:
- `ValidationMode.STRICT`: Hard fail on schema violation
- `ValidationMode.BEST_EFFORT`: Log warning, return anyway

---

### 4. Auto-Repair + Retry (Future: P4-F2)

*Planned for Phase 4*

```yaml
validation:
  retries:
    max_attempts: 2
    repair_prompt: "Fix schema violations only; preserve facts."
```

**Enforces**: LLM gets one chance to self-correct before failing

---

### 5. Idempotent Actions

```python
# Deduplication keys prevent duplicate tickets/alerts
idempotence_keys = [incident_id, action_type]
```

**Enforces**: Same action won't execute twice

---

### 6. Audit Logging

```python
logger.info(
    "LLM call completed",
    extra={
        "model": model_name,
        "model_version": model_version,
        "sampling_preset": preset,
        "temperature": temp,
        "user_id": user_id,
        "request_id": request_id,
    }
)
```

**Enforces**: Every LLM call traceable to model/params/user/time

---

## Measurable SLAs (What We Commit To)

### Primary Metrics

```python
# Schema Validity Rate
SVR = valid_responses / total_responses
# Target: ≥99.5%

# Tool Allowlist Compliance
TAC = unauthorized_tool_calls / total_tool_calls
# Target: 0 (100% compliance)

# Audit Completeness
AC = logged_calls / total_calls
# Target: 100%
```

### Secondary Metrics

```python
# Retrieval Stability (Jaccard overlap)
J = |docs_run_a ∩ docs_run_b| / |docs_run_a ∪ docs_run_b|
# Target: ≥0.80 (same seed/params/index)

# Semantic Equivalence (cosine similarity of embeddings)
cosine_sim(embedding_a, embedding_b) ≥ 0.92
# Target: ≥0.92 for critical fields
```

---

## Configuration Example

```yaml
# Use case configuration (strict preset)
inference:
  mode: strict              # High consistency preset
  temperature: 0.15         # Narrow distribution
  top_p: 0.90               # Focus on high-prob tokens
  max_tokens: 1200
  tool_allow_list:
    - lookup_ticket
    - create_ticket
    - escalate_case

validation:
  json_schema: incident_report_v3.json
  semantic_checks:
    must_include_fields: [incident_id, severity, timestamps]
    severity_domain: [Low, Medium, High, Critical]
  retries:
    max_attempts: 2

retrieval:
  k: 6
  filters:
    time_window_hours: 72
    sources: [IM, SOAR, MISP]
  stability_thresholds:
    jaccard_min: 0.80

enforcement:
  idempotence_keys: [incident_id, action_type]

telemetry:
  log:
    fields: [template_id, model_name, model_version, params_hash, index_snapshot]
  metrics:
    track: [SVR, TAC, AC, jaccard]
  alerts:
    on_breach: [SVR<0.995, TAC>0, AC<1.0]
```

---

## User-Facing Language

### For SOC Analysts (UI/Docs)

> "The Assistant uses AI to generate responses. While we target consistency through controlled settings, the AI may phrase answers differently each time. We validate that outputs meet structural requirements (required fields, approved tools, valid formats) but cannot guarantee factual accuracy. Always verify critical information."

### For Stakeholders (SLAs)

> "We commit to:
> - ≥99.5% schema validity (outputs pass JSON/YAML structural validation)
> - 100% tool policy compliance (only allowlisted tools are invoked)
> - 100% audit completeness (all LLM calls logged with model/version/params)
>
> We target high consistency through controlled sampling (strict preset, low variance settings) but cannot guarantee factual accuracy or semantic correctness. Outputs must be validated by domain experts for critical decisions."

### For Engineers (Code Comments)

```python
# LLMs are stochastic; wrap in deterministic shell for structural guarantees
# What we VALIDATE:
#   - Input: LLM-Guard scanners (PII, prompt injection, toxicity)
#   - Output: JSON schema compliance, required fields, enum domains
#   - Actions: Tool allowlist + idempotence keys
#   - Audit: Full params logged for reproducibility
#
# What we DON'T VALIDATE:
#   - Factual accuracy (LLM may hallucinate)
#   - Semantic correctness (reasoning may be flawed)
#   - Completeness (answer may miss relevant info)
#
# → Analysts must verify critical information
```

---

## Testing Strategy

### 1. Freeze Test Conditions
- Template version
- Model name + version
- Sampling preset
- Retrieval index snapshot

### 2. Run N=50 Iterations
Measure:
- Schema Validity Rate (SVR)
- Tool Allowlist Compliance (TAC)
- Retrieval Jaccard overlap
- Semantic equivalence (cosine similarity)

### 3. Drift Gates
Fail build if:
- `SVR < 0.995`
- `TAC < 1.0`
- `Jaccard < 0.80`

### 4. Canary Deployment
- Small prod slice (5% traffic)
- Monitor identical metrics
- Rollback tied to model version

---

## Where Determinism **Does** Belong

| Component | Should Be Deterministic | Why |
|-----------|------------------------|-----|
| **Validators** | ✅ Yes | Same input → same validation result |
| **Policy gates** | ✅ Yes | Same tools/roles → same allow/deny |
| **State machines** | ✅ Yes | Same state + event → same transition |
| **Idempotence keys** | ✅ Yes | Same key → same deduplication decision |
| **Audit logging** | ✅ Yes | Same call → same log entry |
| **LLM decoding** | ❌ No | Inherently stochastic (sampling from P(·)) |

---

## Critical User Guidance

**For operational decisions (incident severity, escalation, ticket creation):**

> ⚠️ **Human verification required.** The system validates structure and enforces policies, but cannot guarantee factual accuracy. Always review generated content before taking action.

**For informational queries (threat intel summaries, general Q&A):**

> ℹ️ **Best-effort generation.** Outputs are structurally validated and grounded in retrieval sources when available. Verify critical facts through primary sources.

---

## Key Takeaways

1. **LLMs are stochastic by nature**—don't fight it, constrain it
2. **Architecture makes the system reliable**, not the LLM
3. **Guarantee contracts, not wording**—schema validity, tool compliance, audit trails
4. **Measure what you can control**—SVR, TAC, Jaccard, not byte-exact matches
5. **Language matters**—"spec-conformant" over "deterministic"

---

## Further Reading

- [GLOSSARY.md](../user-guides/GLOSSARY.md) - Quick definitions and technical terms
- [ADR-023: Sampling Presets](../development/adrs/ADR-023-Sampling-Presets-and-Guardrails.md) - Preset design decisions
- [TOOL_ALLOWLIST_USAGE.md](TOOL_ALLOWLIST_USAGE.md) - Policy enforcement details
- Google's "Prompt Engineering Guide" (`corpus_docs/22365_3_Prompt Engineering_v7.pdf`)
