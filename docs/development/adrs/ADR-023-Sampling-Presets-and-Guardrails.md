---
id: ADR-023
title: Sampling Presets and Generation Parameter Guardrails
status: Accepted
date: 2025-10-20
implemented: 2025-10-20
deciders: AI Operations Platform Team
related: ADR-018 (Use Case Owned Architecture)
---

## Context

Use Cases currently specify generation parameters (temperature, top_p, max_tokens) as free-form values within bounds (0-1 for temp, etc.). This creates several determinism and quality risks:

### Problems with Current State

1. **High-Entropy Traps:** Users can accidentally create unstable configurations (e.g., `temperature=0.95` + `top_p=0.99` + high top_k) that cause repetition loops or inconsistent outputs.

2. **No Guidance:** Pattern library provides prompt templates but no recommended generation settings, forcing developers to guess optimal parameters.

3. **Lack of Determinism:** SOC workflows require predictable, auditable behavior. Free-form parameter tuning works against this.

4. **ReAct Cost Explosions:** Agentic patterns (ReAct, ToT) without max_tokens caps can produce runaway costs and latencies.

5. **Cross-Parameter Interactions:** Temperature, top_p, and top_k interact in non-obvious ways; no warnings about problematic combinations.

### Research Findings

From Google's "Prompt Engineering" guide (22365_3_Prompt Engineering_v7.pdf):

- Recommends **three variance regimes**: Strict/Low-variance (temp~0.1-0.2), Balanced (temp~0.5-0.7), Creative/High-variance (temp~0.8-0.9)
- Warns about repetition loops at extreme values (very low or very high randomness)
- Advises limiting output length for tool-use patterns
- Emphasizes preset configurations over ad-hoc tuning

### Terminology Note: Stochasticity vs. "Determinism"

**Important conceptual clarification:**

LLMs are **stochastic systems**—they generate tokens by sampling from a probability distribution `P(token|context)`. Even at `temperature=0`, outputs are *more consistent*, not deterministic, due to:

- Floating-point precision variance across hardware
- Model version/checkpoint differences
- Implementation details (GPU kernels, parallelism)

**What we actually achieve:**

- **Bounded variance**: Presets shape the distribution to produce *functionally equivalent* outputs
- **Spec-conformant behavior**: Validators enforce schema/policy compliance regardless of wording variance
- **High repeatability**: Same preset + model version + seed produces similar (not identical) results

**Architectural pattern**: We wrap the stochastic core (LLM) in a deterministic shell (validators, policy gates, audit logs) to make the *system* reliable even if the *LLM* varies.

**User-facing language:**

- ❌ Don't say: "Deterministic mode guarantees identical outputs"
- ✅ Do say: "Strict preset produces highly consistent, validated outputs"

See: [`docs/architecture/CONSISTENCY_MODEL.md`](../../architecture/CONSISTENCY_MODEL.md), [`docs/user-guides/GLOSSARY.md`](../../user-guides/GLOSSARY.md) for the full pattern.

## Decision

We implement a **Sampling Preset System** with policy-based guardrails:

### 1. Predefined Sampling Presets

Three canonical presets bound to use case intent:

```python
class SamplingPreset(str, Enum):
    """Predefined sampling configurations for variance control."""
    STRICT = "strict"        # High consistency, low variance
    BALANCED = "balanced"    # Good general-purpose default
    CREATIVE = "creative"    # Exploratory, high variance
    CUSTOM = "custom"        # User-defined (requires override permission)
```

**Preset Configurations:**

| Preset | Temperature | Top-P | Top-K (if applicable) | Max Tokens | Use Cases |
|--------|-------------|-------|---------------------|------------|-----------|
| **Strict** | 0.1-0.2 | 0.90 | 20 | 1024 | Threat triage, IOC extraction, classification |
| **Balanced** | 0.5-0.7 | 0.95 | 30 | 2048 | General Q&A, summarization, RAG queries |
| **Creative** | 0.8-0.9 | 0.97 | 40 | 4096 | Playbook drafting, scenario generation |

### 2. Pattern Library Integration

**Update `prompt_patterns` schema:**

```sql
ALTER TABLE prompt_patterns
ADD COLUMN recommended_preset VARCHAR(50) DEFAULT 'balanced',
ADD COLUMN max_tokens_override INT,
ADD COLUMN special_params JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN prompt_patterns.recommended_preset IS
  'Recommended sampling preset for this pattern (strict, balanced, creative)';
COMMENT ON COLUMN prompt_patterns.max_tokens_override IS
  'Override max_tokens for patterns with specific needs (e.g., ReAct with tool use)';
```

**Example Pattern Binding:**

```json
{
  "pattern_id": "react-with-retrieval",
  "name": "ReAct with RAG Citations",
  "category": "tools",
  "recommended_preset": "balanced",
  "max_tokens_override": 2048,
  "special_params": {
    "max_tool_steps": 5,
    "tool_step_timeout": 30
  }
}
```

### 3. Use Case Configuration Schema Update

**Update `GenerationParamsConfig`:**

```python
class GenerationParamsConfig(BaseModel):
    """Configuration for LLM generation parameters."""

    # Preset-based configuration (preferred)
    sampling_preset: SamplingPreset = Field(
        default=SamplingPreset.BALANCED,
        description="Predefined sampling configuration"
    )

    # Legacy/override fields (require policy permission)
    temperature: float | None = Field(
        default=None,  # Derived from preset if None
        description="Temperature override (requires CUSTOM preset)",
        ge=0.0, le=1.0
    )
    max_tokens: int | None = Field(
        default=None,  # Derived from preset if None
        description="Max tokens override",
        gt=0, le=16384
    )
    top_p: float | None = Field(
        default=None,  # Derived from preset if None
        description="Top-p override (requires CUSTOM preset)",
        ge=0.0, le=1.0
    )

    # Policy constraints
    max_tool_steps: int | None = Field(
        default=None,
        description="Maximum tool invocation steps (for ReAct patterns)",
        ge=1, le=10
    )
    tool_step_timeout: int = Field(
        default=30,
        description="Timeout per tool step (seconds)",
        ge=5, le=120
    )

    # Existing fields
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)

    @validator("temperature", "top_p")
    def validate_custom_override(cls, v, values, field):
        """Custom parameters require CUSTOM preset."""
        if v is not None and values.get("sampling_preset") != SamplingPreset.CUSTOM:
            raise ValueError(
                f"{field.name} override requires sampling_preset='custom'. "
                f"Current preset: {values.get('sampling_preset')}"
            )
        return v

    def get_effective_params(self) -> dict[str, Any]:
        """
        Resolve effective parameters from preset + overrides.

        Returns:
            Dictionary with resolved temperature, top_p, max_tokens
        """
        preset_configs = {
            SamplingPreset.STRICT: {
                "temperature": 0.15,
                "top_p": 0.90,
                "max_tokens": 1024
            },
            SamplingPreset.BALANCED: {
                "temperature": 0.65,
                "top_p": 0.95,
                "max_tokens": 2048
            },
            SamplingPreset.CREATIVE: {
                "temperature": 0.85,
                "top_p": 0.97,
                "max_tokens": 4096
            }
        }

        if self.sampling_preset == SamplingPreset.CUSTOM:
            # Use explicit overrides
            return {
                "temperature": self.temperature or 0.7,
                "top_p": self.top_p or 0.95,
                "max_tokens": self.max_tokens or 2048
            }

        # Use preset configuration
        base = preset_configs[self.sampling_preset].copy()

        # Allow max_tokens override even with preset
        if self.max_tokens is not None:
            base["max_tokens"] = self.max_tokens

        return base
```

### 4. Guardrail Validation Rules

**High-Entropy Detection:**

```python
@validator("sampling_preset", "temperature", "top_p")
def validate_high_entropy_trap(cls, v, values):
    """Detect and warn about high-entropy configurations."""
    temp = values.get("temperature")
    top_p = values.get("top_p")

    # Check if we have custom values
    if temp is not None and top_p is not None:
        # High-entropy trap: both temp and top_p very high
        if temp > 0.9 and top_p > 0.97:
            logger.warning(
                "High-entropy configuration detected: "
                f"temperature={temp}, top_p={top_p}. "
                "This may cause repetition loops or inconsistent outputs."
            )

        # Low-entropy trap: both very low
        if temp < 0.1 and top_p < 0.85:
            logger.warning(
                "Very low-entropy configuration: "
                f"temperature={temp}, top_p={top_p}. "
                "May produce repetitive outputs."
            )

    return v
```

### 5. RBAC Policy Integration

**Add to `PolicyConfig`:**

```python
class PolicyConfig(BaseModel):
    # ... existing fields ...

    allow_custom_sampling: bool = Field(
        default=False,
        description="Whether users can override preset with custom parameters"
    )
    enforce_max_tokens: bool = Field(
        default=True,
        description="Strictly enforce max_tokens limit (prevents runaway costs)"
    )
    require_preset_approval: bool = Field(
        default=False,
        description="Require admin approval to change sampling preset"
    )
```

**RBAC Matrix:**

| Role | Can Use Presets | Can Use CUSTOM | Can Override max_tokens | Can Change Preset |
|------|----------------|----------------|------------------------|-------------------|
| **analyst** | ✅ | ❌ | ❌ | ❌ |
| **use_case_publisher** | ✅ | ✅ (with warning) | ✅ (within bounds) | ✅ (draft only) |
| **corpus_admin** | ✅ | ✅ | ✅ | ✅ |
| **admin** | ✅ | ✅ | ✅ | ✅ |

## Consequences

### Positive

✅ **Consistency by Default**

- Analysts get predictable, validated outputs without parameter tuning
- Preset names communicate intent ("strict" = high consistency, validated outputs)

✅ **Cost Control**

- max_tokens caps prevent runaway costs
- max_tool_steps prevents ReAct loops
- Policy enforcement at configuration time, not runtime

✅ **Pattern Library Guidance**

- Each pattern comes with recommended settings
- Developers start with known-good configurations
- Reduces trial-and-error cycles

✅ **Auditability**

- "Used 'strict' preset" is clear in audit logs
- No hidden parameter tweaking
- Configuration drift visible in version history

✅ **Enterprise Safety**

- High-entropy warnings prevent accidental misconfiguration
- RBAC controls who can experiment with CUSTOM
- Immutable published Use Cases ensure stable behavior

### Negative

⚠️ **Migration Complexity**

- Existing Use Cases with explicit parameters need migration
- Default all to SamplingPreset.BALANCED with overrides
- UI must support both preset and custom modes

⚠️ **Reduced Flexibility**

- Power users may want fine-grained control
- Mitigated by CUSTOM preset with override permissions

⚠️ **Model Compatibility**

- Some models don't support all parameters (e.g., no top_k in GPT-4)
- Presets must be model-aware or ignore unsupported params

### Mitigations

**Migration Strategy:**

1. Default existing UCs to `sampling_preset=balanced`
2. Preserve explicit temp/top_p as overrides if different from balanced
3. Set `allow_custom_sampling=true` for all existing UCs initially
4. Gradual rollout: new UCs start with presets, old UCs grandfathered

**Model Compatibility:**

```python
def apply_preset_to_model(
    preset_params: dict,
    model_id: str
) -> dict:
    """Filter preset params to model-supported subset."""
    model_capabilities = get_model_capabilities(model_id)

    filtered = {}
    for param, value in preset_params.items():
        if param in model_capabilities.supported_params:
            filtered[param] = value

    return filtered
```

## Implementation Plan

### Phase 1: Schema & Backend (1-2 days)

1. **Update Schemas:**
   - Add `SamplingPreset` enum
   - Update `GenerationParamsConfig` with preset field
   - Add preset recommendation to `prompt_patterns`
   - Add policy flags to `PolicyConfig`

2. **Migration:**
   - Add `recommended_preset` column to `prompt_patterns`
   - Seed presets for existing 29 patterns
   - Add data migration for existing Use Cases

3. **Validation:**
   - Implement high-entropy detection
   - Add `get_effective_params()` resolution logic
   - Update orchestrator to use effective params

### Phase 2: Pattern Library Seeding (1 day)

**Update existing patterns with recommended presets:**

```sql
UPDATE prompt_patterns
SET recommended_preset = 'strict',
    max_tokens_override = 1024
WHERE category IN ('classification', 'extraction', 'triage');

UPDATE prompt_patterns
SET recommended_preset = 'balanced',
    max_tokens_override = 2048
WHERE category IN ('rag', 'qa', 'summarization');

UPDATE prompt_patterns
SET recommended_preset = 'creative',
    max_tokens_override = 4096
WHERE category IN ('generation', 'brainstorming', 'scenario');

UPDATE prompt_patterns
SET recommended_preset = 'balanced',
    max_tokens_override = 2048,
    special_params = '{"max_tool_steps": 5, "tool_step_timeout": 30}'::jsonb
WHERE pattern_id LIKE '%react%' OR category = 'tools';
```

### Phase 3: Frontend UI (2-3 days)

**Use Case Wizard Updates:**

```typescript
// Sampling preset selector in Step 4 (Configure)
<mat-form-field>
  <mat-label>Sampling Preset</mat-label>
  <mat-select formControlName="samplingPreset">
    <mat-option value="strict">
      <strong>Strict</strong> - High consistency, low variance
      <br><small>Temp: 0.15, Top-P: 0.90</small>
    </mat-option>
    <mat-option value="balanced">
      <strong>Balanced</strong> - Good general-purpose default
      <br><small>Temp: 0.65, Top-P: 0.95</small>
    </mat-option>
    <mat-option value="creative">
      <strong>Creative</strong> - Exploratory, varied outputs
      <br><small>Temp: 0.85, Top-P: 0.97</small>
    </mat-option>
    <mat-option value="custom" *ngIf="canUseCustomSampling">
      <strong>Custom</strong> - Advanced parameters
      <br><small>Requires override permission</small>
    </mat-option>
  </mat-select>
  <mat-hint>Recommended for this pattern: {{ patternPreset }}</mat-hint>
</mat-form-field>

<!-- Show warning for high-entropy configs -->
<mat-error *ngIf="isHighEntropyConfig()">
  ⚠️ High-entropy configuration may cause inconsistent outputs
</mat-error>

<!-- Custom parameter section (only if preset = CUSTOM) -->
<div *ngIf="samplingPreset === 'custom'" class="custom-params">
  <mat-form-field>
    <mat-label>Temperature</mat-label>
    <input matInput type="number" formControlName="temperature"
           min="0" max="1" step="0.05">
  </mat-form-field>
  <!-- ... other custom fields ... -->
</div>
```

**Pattern Library Enhancement:**

- Show preset badge on pattern cards
- Auto-apply preset when pattern selected in wizard
- Display warning if user changes from recommended preset

### Phase 4: Documentation & Training (1 day)

1. Update Use Case management guide with preset explanations
2. Add sampling preset section to pattern library docs
3. Create decision matrix: "Which preset should I use?"
4. Update API documentation with preset examples

## Testing Strategy

```python
# Unit tests
def test_preset_resolution_strict():
    config = GenerationParamsConfig(sampling_preset=SamplingPreset.STRICT)
    params = config.get_effective_params()
    assert params["temperature"] == 0.15
    assert params["top_p"] == 0.90
    assert params["max_tokens"] == 1024

def test_custom_preset_requires_overrides():
    with pytest.raises(ValidationError):
        GenerationParamsConfig(
            sampling_preset=SamplingPreset.BALANCED,
            temperature=0.99  # Error: requires CUSTOM preset
        )

def test_high_entropy_detection(caplog):
    config = GenerationParamsConfig(
        sampling_preset=SamplingPreset.CUSTOM,
        temperature=0.95,
        top_p=0.99
    )
    assert "high-entropy configuration" in caplog.text.lower()

# Integration tests
@pytest.mark.integration
async def test_orchestrator_applies_preset():
    use_case = create_test_use_case(sampling_preset="strict")
    response = await orchestrator.process_request(query="test", use_case_id=use_case.id)

    # Verify LLM was called with preset params
    assert llm_mock.last_request.temperature == 0.15
    assert llm_mock.last_request.top_p == 0.90
```

## Acceptance Criteria

- [ ] Three sampling presets defined (strict, balanced, creative)
- [ ] Pattern library patterns tagged with recommended presets
- [ ] Use Case configuration supports preset selection
- [ ] CUSTOM preset requires appropriate RBAC permissions
- [ ] High-entropy warning system functional
- [ ] `get_effective_params()` resolves preset → explicit params
- [ ] Orchestrator uses effective params in LLM calls
- [ ] Frontend wizard shows preset selector with recommendations
- [ ] Migration script converts existing UCs to preset format
- [ ] Documentation updated with preset guidance
- [ ] Integration tests verify preset behavior
- [ ] max_tool_steps prevents ReAct runaway costs

## References

- **Source:** Google "Prompt Engineering" guide (22365_3_Prompt Engineering_v7.pdf)
- **Related:** ADR-018 (Use Case Owned Architecture)
- **Related:** P3-F6 (Use Case Validation & Testing) - linter integration
- **Schema:** `src/orchestrator/app/schemas/use_case_config.py`
- **Patterns:** `ops/migrations/sql/012_prompt_patterns.sql`

## Future Enhancements

**Phase 5+:**

1. **Model-Specific Presets:**
   - Different preset values per model family
   - GPT-4 presets vs Llama presets vs Mistral presets

2. **Adaptive Presets:**
   - Learn optimal parameters from successful queries
   - Auto-suggest preset adjustments based on metrics

3. **A/B Testing:**
   - Compare preset performance side-by-side
   - Measure determinism, quality, cost trade-offs

4. **Extended Guardrails:**
   - Detect token budget violations
   - Warn about expensive tool use patterns
   - Suggest cheaper alternatives

---

**Status:** ✅ Accepted & Implemented
**Completed:** Phase 4 (October 20, 2025)
**Priority:** High (determinism critical for enterprise)
**Actual Effort:** 3 hours (estimated 5-7 days)
