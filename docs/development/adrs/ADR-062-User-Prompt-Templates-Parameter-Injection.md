# ADR-062: User Prompt Templates with Parameter Injection

**Status:** Proposed
**Date:** 2026-02-04
**Deciders:** AI Operations Platform Team
**Tags:** use-case, prompts, templates, parameters, ux

---

## Context

**What is the issue we're addressing?**

The AI Operations Platform enables AI Ops developers to create use cases that accept user inputs at execution time. Currently, when users provide input field values, they are concatenated as simple `"key: value"` strings:

```python
# Current implementation (use_cases.py:438-445)
query_parts = []
for field_name, field_value in execution.inputs.items():
    query_parts.append(f"{field_name}: {field_value}")
query_text = "\n".join(query_parts)
```

This approach has significant limitations:

1. **No narrative control** - AI Ops developers cannot frame parameters within context
2. **Suboptimal prompts** - Generic concatenation doesn't leverage prompt engineering best practices
3. **Poor LLM performance** - Prompts are not optimized for specific models or tasks
4. **Limited expressiveness** - Cannot create sophisticated multi-parameter interactions

**Session note:** The `user_prompt_template` field was explicitly removed in an earlier session (`docs/development/sessions/2025-10-19-p3-multi-role-prompts.md`) but the capability is now needed.

**What needs to be decided?** How to enable AI Ops developers to define templates with parameter placeholders that are rendered at execution time.

---

## Decision

**What did we decide?**

Introduce an optional `user_prompt_template` configuration that allows AI Ops developers to define templates with `{{variable}}` placeholders that are substituted with input field values at execution time.

**Key implementation details:**

### 1. Schema Addition

```python
# src/orchestrator/app/schemas/use_case_config.py

class UserPromptTemplateConfig(BaseModel):
    """Configuration for user-facing prompt template with variable injection."""

    template: str = Field(
        description="User prompt template with {{variable}} placeholders"
    )
    variables: list[str] = Field(
        default_factory=list,
        description="Declared variables (auto-extracted if empty)"
    )
    fallback_mode: Literal["concatenate", "error"] = Field(
        default="concatenate",
        description="Behavior when input field missing: concatenate (legacy) or error"
    )

class UseCaseConfig(BaseModel):
    # ... existing fields ...

    user_prompt_template: UserPromptTemplateConfig | None = Field(
        default=None,
        description="Optional user prompt template. If None, uses legacy concatenation."
    )
```

### 2. Template Rendering

```python
# New: src/orchestrator/app/orchestrator/template_renderer.py

import re
VARIABLE_PATTERN = re.compile(r'\{\{(\w+)\}\}')

def render_user_prompt_template(
    template: str,
    inputs: dict[str, Any],
    fallback_mode: str = "concatenate"
) -> str:
    """Render user prompt template with input values."""
    def replace_variable(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name in inputs:
            return str(inputs[var_name])
        elif fallback_mode == "error":
            raise ValueError(f"Missing required variable: {var_name}")
        else:
            return f"[{var_name}: not provided]"

    return VARIABLE_PATTERN.sub(replace_variable, template)
```

### 3. Execution Path Integration

```python
# Modified execution logic
if use_case_config.user_prompt_template:
    query_text = render_user_prompt_template(
        template=use_case_config.user_prompt_template.template,
        inputs=execution.inputs,
        fallback_mode=use_case_config.user_prompt_template.fallback_mode
    )
else:
    # Legacy concatenation (backward compatible)
    query_text = "\n".join(f"{k}: {v}" for k, v in execution.inputs.items())
```

### 4. Variable Syntax

**Chosen syntax:** `{{variable_name}}`

| Syntax | Pros | Cons |
|--------|------|------|
| `{{variable}}` | Jinja-like, familiar | Could conflict with JSON in prompt |
| `{variable}` | Python-native | Conflicts with JSON literal braces |
| `${variable}` | Shell-like, unambiguous | Less familiar |

**Decision:** Use `{{variable}}` with smart parsing that only matches known variable names.

---

## Alternatives Considered

### Option 1: Jinja2 Templates

**Description:** Use full Jinja2 templating engine for prompts.

**Pros:**
- Powerful: conditionals, loops, filters
- Industry standard
- Familiar to many developers

**Cons:**
- Security concerns (code execution in templates)
- Overkill for simple variable substitution
- Additional dependency
- Harder to validate in UI

**Why Rejected:** Complexity and security concerns outweigh benefits for this use case.

### Option 2: Python Format Strings

**Description:** Use `{variable}` syntax with Python's `str.format()`.

**Pros:**
- Native Python, no regex needed
- Very fast

**Cons:**
- Conflicts with JSON braces in prompts
- Requires escaping `{{` for literal braces
- Error-prone for users

**Why Rejected:** JSON in prompts is common; brace conflicts are too frequent.

### Option 3: Custom DSL

**Description:** Create a domain-specific language for prompts.

**Pros:**
- Full control over syntax
- Can add advanced features

**Cons:**
- Steep learning curve
- Maintenance burden
- No tooling ecosystem

**Why Rejected:** Over-engineering for current requirements.

---

## Consequences

### Positive Consequences

- AI Ops developers gain full control over user message structure
- Prompts can be optimized for specific LLMs and tasks
- Better user experience with contextual framing of inputs
- Supports prompt engineering best practices

### Negative Consequences

- Additional complexity in execution path
- Need for template validation in wizard UI
- Potential for malformed templates causing execution failures

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Template syntax errors | Medium | Real-time validation in wizard UI |
| Variable name mismatches | Medium | Auto-extract variables; validate against input_fields |
| Breaking existing use cases | Low | Fully backward compatible (optional field, defaults to legacy) |
| Injection attacks | Low | Only substitute known variables; no code execution |

---

## Implementation Notes

**Files affected:**
- `src/orchestrator/app/schemas/use_case_config.py` - Add UserPromptTemplateConfig
- `src/orchestrator/app/routers/use_cases.py` - Modify execution to use template
- `src/orchestrator/app/orchestrator/template_renderer.py` - New file for rendering logic
- `src/frontend-angular/src/app/api/models/use-case.models.ts` - Add TypeScript types
- `src/frontend-angular/src/app/pages/use-cases/use-case-wizard.component.*` - Add template editor

**Migration steps:**
- None required (additive change)
- Existing use cases continue to work unchanged

**Dependencies:**
- None (uses standard library regex)

**Testing strategy:**
- Unit tests for template_renderer.py
- Integration tests for execution with templates
- E2E tests for wizard template editor

---

## References

- Implementation Plan: `docs/development/plans/features/active/USE_CASE_AUTHORING_COMPLETE_SPEC.md`
- Discovery: `docs/development/analysis/AI_OPS_USE_CASE_AND_STRUCTURED_OUTPUT_DISCOVERY.md`
- ADR-018: Use Case Owned Architecture
- ADR-044: Use Cases as Bounded Refinement Spaces

---

## Status Updates

### 2026-02-04 - Proposed

**Changed By:** AI Operations Platform Team
**Reason:** Initial proposal based on discovery analysis and implementation planning.

---

**Template Version:** 1.0
**Based On:** Michael Nygard's ADR pattern
