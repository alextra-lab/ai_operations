# Creating Custom Validation Rules - Developer Guide

**Purpose:** Learn how to create custom validation rules for Use Cases.

**Target Audience:** Backend Developers, Platform Administrators

**Last Updated:** October 21, 2025

---

## Overview

The validation engine uses an extensible rule system that allows adding custom validation logic without modifying core code.

### Architecture

```
ValidationEngine
├── register_rule(rule: ValidationRule)
└── validate_use_case(use_case: dict) → ValidationReport
    ├── Runs all registered rules
    ├── Groups issues by severity
    └── Returns aggregated report

ValidationRule (base class)
├── rule_id: str
├── name: str
├── description: str
├── severity: ValidationSeverity
└── validate(use_case: dict) → list[ValidationIssue]
```

---

## Creating a Validation Rule

### Step 1: Implement ValidationRule

```python
# File: src/orchestrator/app/services/validation/custom_rules.py

from typing import Any
from .validation_engine import ValidationRule, ValidationIssue, ValidationSeverity

class MyCustomRule(ValidationRule):
    """Description of what this rule validates."""

    rule_id = "my-custom-rule"  # Unique identifier (kebab-case)
    name = "My Custom Rule"  # Human-readable name
    description = "Validates X to ensure Y"  # What it checks
    severity = ValidationSeverity.WARNING  # ERROR | WARNING | INFO

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """
        Validate Use Case and return issues.

        Args:
            use_case: Use Case configuration dictionary
                - use_case_id: str
                - config_json: dict (generation_params, output_contract, rag, tools_allowlist)
                - metadata_json: dict (prompts, pattern_id, tags)

        Returns:
            List of ValidationIssue objects (empty if valid)
        """
        issues: list[ValidationIssue] = []

        # Access Use Case configuration
        config_json = use_case.get("config_json", {})
        metadata_json = use_case.get("metadata_json", {})

        # Your validation logic here
        if some_condition_fails:
            issues.append(
                ValidationIssue(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    message="Clear, actionable error message",
                    field="config_json.generation_params.temperature",  # Optional
                    suggestion="How to fix the issue",  # Optional
                    auto_fix={"generation_params": {"temperature": 0.7}},  # Optional
                )
            )

        return issues
```

### Step 2: Register the Rule

```python
# File: src/orchestrator/app/services/validation/validation_engine.py

def _register_default_rules(self) -> None:
    """Register built-in validation rules."""
    from .prompt_rules import (...)
    from .config_rules import (...)
    from .custom_rules import MyCustomRule  # Import your rule

    # ... existing rules ...

    # Register your rule
    self.register_rule(MyCustomRule())
```

---

## Rule Examples

### Example 1: Simple Field Validation

```python
class MaxTokensLimitRule(ValidationRule):
    """Ensure max_tokens doesn't exceed model limit."""

    rule_id = "max-tokens-limit"
    name = "Max Tokens Limit"
    description = "Validates max_tokens is within model limits"
    severity = ValidationSeverity.ERROR

    MAX_TOKENS_LIMIT = 4096

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        issues = []

        config_json = use_case.get("config_json", {})
        gen_params = config_json.get("generation_params", {})
        max_tokens = gen_params.get("max_tokens")

        if max_tokens and max_tokens > self.MAX_TOKENS_LIMIT:
            issues.append(
                ValidationIssue(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    message=f"max_tokens ({max_tokens}) exceeds limit ({self.MAX_TOKENS_LIMIT})",
                    field="config_json.generation_params.max_tokens",
                    suggestion=f"Reduce max_tokens to {self.MAX_TOKENS_LIMIT} or lower",
                    auto_fix={"generation_params": {"max_tokens": self.MAX_TOKENS_LIMIT}},
                )
            )

        return issues
```

### Example 2: Cross-Field Validation

```python
class TemperatureTopPConsistencyRule(ValidationRule):
    """Ensure temperature and top_p are consistent."""

    rule_id = "temperature-topp-consistency"
    name = "Temperature and Top-P Consistency"
    description = "Validates temperature and top_p are in reasonable ranges"
    severity = ValidationSeverity.WARNING

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        issues = []

        config_json = use_case.get("config_json", {})
        gen_params = config_json.get("generation_params", {})

        temp = gen_params.get("temperature")
        top_p = gen_params.get("top_p")

        # Both should be set or both unset
        if (temp is not None) != (top_p is not None):
            issues.append(
                ValidationIssue(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    message="temperature and top_p should both be set or both use defaults",
                    field="config_json.generation_params",
                    suggestion="Set both temperature and top_p explicitly or use a preset",
                )
            )

        return issues
```

### Example 3: Pattern-Specific Validation

```python
class FewShotPatternRule(ValidationRule):
    """Ensure few-shot patterns have examples."""

    rule_id = "fewshot-pattern-examples"
    name = "Few-Shot Pattern Examples"
    description = "Validates few-shot patterns have at least 2 examples"
    severity = ValidationSeverity.ERROR

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        issues = []

        metadata_json = use_case.get("metadata_json", {})
        pattern_id = metadata_json.get("pattern_id", "")
        prompts = metadata_json.get("prompts", {})
        fewshots = prompts.get("fewshots", [])

        # Only validate if pattern is few-shot
        if "few-shot" in pattern_id.lower():
            if len(fewshots) < 2:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        message=f"Few-shot pattern requires at least 2 examples (found {len(fewshots)})",
                        field="metadata_json.prompts.fewshots",
                        suggestion="Add at least 2 few-shot examples demonstrating desired behavior",
                    )
                )

        return issues
```

---

## Validation Issue Fields

### Required Fields

```python
ValidationIssue(
    rule_id="my-rule-id",              # Unique rule identifier
    severity=ValidationSeverity.ERROR,  # ERROR | WARNING | INFO
    message="Clear error message",      # User-facing message
)
```

### Optional Fields

```python
ValidationIssue(
    # ... required fields ...
    field="config_json.rag.enabled",        # Field path (dot notation)
    suggestion="Recommended fix",           # Actionable suggestion
    auto_fix={"rag": {"enabled": False}},   # Auto-fix payload (deep merged)
)
```

---

## Auto-Fix Payloads

Auto-fix payloads are deep-merged into `config_json`:

```python
# Original config
config_json = {
    "generation_params": {
        "temperature": 0.95,
        "top_p": 0.99,
        "max_tokens": 1024
    }
}

# Auto-fix payload
auto_fix = {
    "generation_params": {
        "sampling_preset": "balanced",
        "temperature": None,  # Explicit None removes field
        "top_p": None
    }
}

# Result (deep merged)
config_json = {
    "generation_params": {
        "sampling_preset": "balanced",  # Added
        # temperature and top_p removed
        "max_tokens": 1024  # Preserved
    }
}
```

---

## Testing Validation Rules

### Unit Test Template

```python
# File: src/orchestrator/tests/unit/services/test_custom_rules.py

import pytest
from src.backend.app.services.validation.custom_rules import MyCustomRule
from src.backend.app.services.validation import ValidationSeverity

class TestMyCustomRule:
    """Tests for MyCustomRule."""

    def test_valid_use_case(self):
        """Test that valid Use Case passes validation."""
        rule = MyCustomRule()
        use_case = {
            "config_json": {"key": "valid_value"},
            "metadata_json": {}
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0

    def test_invalid_use_case(self):
        """Test that invalid Use Case triggers issue."""
        rule = MyCustomRule()
        use_case = {
            "config_json": {"key": "invalid_value"},
            "metadata_json": {}
        }

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.WARNING
        assert "invalid" in issues[0].message.lower()

    def test_auto_fix(self):
        """Test that auto-fix is provided when applicable."""
        rule = MyCustomRule()
        use_case = {
            "config_json": {"key": "invalid_value"},
            "metadata_json": {}
        }

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].auto_fix is not None
        assert "key" in issues[0].auto_fix
```

---

## Best Practices

### 1. Clear, Actionable Messages

❌ Bad:
```python
message="Invalid configuration"
```

✅ Good:
```python
message="temperature (0.95) is too high. High temperatures may cause inconsistent outputs."
```

### 2. Provide Suggestions

❌ Bad:
```python
suggestion=None
```

✅ Good:
```python
suggestion="Use 'balanced' preset (temp=0.65, top_p=0.95) for consistent results"
```

### 3. Use Appropriate Severity

- **ERROR:** Blocks publish, must be fixed (e.g., missing required field, invalid schema)
- **WARNING:** Review recommended, can publish with confirmation (e.g., high entropy, short prompt)
- **INFO:** Suggestion only, doesn't affect publish (e.g., insufficient few-shots)

### 4. Handle Missing Fields Gracefully

```python
config_json = use_case.get("config_json", {})  # Default to {}
gen_params = config_json.get("generation_params", {})
max_tokens = gen_params.get("max_tokens")  # May be None

if max_tokens is not None:  # Check before using
    # validation logic
```

### 5. Test Edge Cases

- Missing fields
- Null values
- Empty arrays/strings
- Unexpected types

---

## Debugging Validation Rules

### Enable Debug Logging

```python
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
    logger.debug(f"Validating Use Case {use_case.get('use_case_id')}")
    logger.debug(f"Config: {use_case.get('config_json')}")
    # ... validation logic ...
```

### Use Validation API Directly

```bash
# Test validation via API
curl -X POST http://localhost:8006/api/v1/use-cases/test-001/validate \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

### Run Unit Tests

```bash
pytest src/orchestrator/tests/unit/services/test_custom_rules.py -v
```

---

## Common Patterns

### Pattern 1: Require Field If Condition Met

```python
if condition_is_true:
    if not required_field:
        issues.append(ValidationIssue(...))
```

### Pattern 2: Validate Range

```python
if value < min_value or value > max_value:
    issues.append(ValidationIssue(...))
```

### Pattern 3: Mutual Exclusion

```python
if field_a and field_b:
    issues.append(ValidationIssue(
        message="Only one of field_a or field_b can be set"
    ))
```

### Pattern 4: Dependency Validation

```python
if parent_field_enabled:
    if not child_field:
        issues.append(ValidationIssue(...))
```

---

## API Reference

### ValidationRule

```python
class ValidationRule:
    rule_id: str               # Unique identifier (kebab-case)
    name: str                  # Human-readable name
    description: str           # What the rule validates
    severity: ValidationSeverity  # ERROR | WARNING | INFO

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """Validate Use Case and return issues."""
        raise NotImplementedError
```

### ValidationIssue

```python
class ValidationIssue(BaseModel):
    rule_id: str               # Rule that generated this issue
    severity: ValidationSeverity  # Issue severity
    message: str               # User-facing message
    field: str | None          # Field path (optional)
    suggestion: str | None     # Fix suggestion (optional)
    auto_fix: dict | None      # Auto-fix payload (optional)
```

### ValidationReport

```python
class ValidationReport(BaseModel):
    use_case_id: str           # Use Case ID
    is_valid: bool             # No errors
    can_publish: bool          # No blocking errors
    issues: list[ValidationIssue]  # All issues
    errors: list[ValidationIssue]  # Error issues
    warnings: list[ValidationIssue]  # Warning issues
    infos: list[ValidationIssue]  # Info issues
    validated_at: datetime     # Validation timestamp
```

---

## Related Documentation

- [Use Case Validation User Guide](../../user-guides/use-case-validation.md)
- [ADR-023: Sampling Presets](../adrs/ADR-023-Sampling-Presets-and-Guardrails.md)
- [Validation Engine Source](../../../src/orchestrator/app/services/validation/validation_engine.py)

---

**Questions?** Contact the platform development team or refer to the [Developer Documentation](../README.md).
