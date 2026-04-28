# P3-F6: Use Case Validation & Testing

**Status:** ✅ COMPLETED (October 21, 2025)
**Priority:** High (Must-Complete from Phase 3)
**Actual Time:** 1 day
**Phase:** Phase 4 - Security & Enterprise Features
**Date Created:** October 20, 2025
**Date Completed:** October 21, 2025
**Dependencies:** ADR-023 (Sampling Presets) ✅, P3-F2 (Use Case Management) ✅

---

## Executive Summary

Implement a comprehensive Use Case validation and testing framework that ensures quality, consistency, and determinism before deployment. Includes a prompt linter, configuration validator, test query interface, and automated testing capabilities.

**Key Value Proposition:** Prevent misconfigured Use Cases from reaching production, reduce trial-and-error cycles, and provide developers with confidence that their Use Cases will behave predictably.

---

## Background

### Current State

**Existing Validation:**
- ✅ Pydantic schema validation (`UseCaseConfig`)
- ✅ Basic field-level constraints (temperature 0-1, max_tokens > 0)
- ✅ RAG config validation (collections exist, top_k > 0)
- ✅ Tool allowlist validation (strings only)

**Gaps:**
- ❌ No prompt quality checks (high-entropy parameters, missing instructions)
- ❌ No test query interface (can't validate behavior before publishing)
- ❌ No automated testing with sample inputs
- ❌ No configuration best-practice checks
- ❌ No cross-field validation (e.g., ReAct pattern + max_tool_steps)
- ❌ No regression testing framework

### Problem Statement

**Scenario 1: High-Entropy Trap**
```python
# Developer creates Use Case with dangerous settings
config = {
  "generation_params": {
    "sampling_preset": "custom",
    "temperature": 0.95,  # Very high
    "top_p": 0.99         # Very high
  }
}
# No warning issued → inconsistent outputs in production
```

**Scenario 2: Missing Instructions**
```python
# Use Case has no system prompt guidance
prompts = {
  "system_prompt": "You are an analyst.",  # Too vague
  "developer_prompt": None,                # Missing
  "fewshots": []                           # No examples
}
# Result: LLM guesses intent, variable output quality
```

**Scenario 3: Untested Configuration**
```
Developer creates Use Case
→ Sets lifecycle_state = "published"
→ No test queries run
→ Analysts use it in production
→ Discovers it doesn't work as expected
→ Emergency rollback required
```

---

## Objectives

### Primary Goals

1. **Prompt Linter:** Automated quality checks for prompts and configuration
2. **Test Query Interface:** Validate Use Case behavior with sample queries
3. **Automated Testing:** Run test suites against Use Case configurations
4. **Validation Reports:** Clear, actionable feedback on issues
5. **Integration:** Validation hooks in Use Case wizard (save-time checks)

### Success Criteria

- [ ] Prompt linter catches 5+ classes of issues
- [ ] High-entropy trap detection functional
- [ ] Test query interface in Use Case wizard
- [ ] Automated test runner for regression testing
- [ ] Validation reports with severity levels (error, warning, info)
- [ ] Configurable validation rules per organization
- [ ] Performance: < 500ms for full validation
- [ ] Integration with Use Case lifecycle (block publish if errors)
- [ ] Documentation for validation rules

---

## Architecture

### Component Overview

```
┌──────────────────────────────────────────────────────────┐
│              Use Case Wizard / Editor                     │
│                                                           │
│  [Save Use Case]                                          │
│         ↓                                                 │
│  ┌─────────────────────────────────────┐                 │
│  │   Validation Orchestrator           │                 │
│  │                                      │                 │
│  │  1. Prompt Linter                   │                 │
│  │  2. Config Validator                │                 │
│  │  3. Pattern Compliance Checker      │                 │
│  │  4. Cross-field Validator           │                 │
│  └─────────────────┬───────────────────┘                 │
│                    │                                      │
│                    ↓                                      │
│  ┌─────────────────────────────────────┐                 │
│  │    Validation Report                │                 │
│  │                                      │                 │
│  │  ⚠️ 2 Errors (blocks publish)       │                 │
│  │  ⚠️ 3 Warnings (review recommended) │                 │
│  │  ℹ️ 1 Info (suggestion)            │                 │
│  └─────────────────────────────────────┘                 │
│                                                           │
│  [Fix Issues] [Publish Anyway (admin)] [Test Query]      │
└──────────────────────────────────────────────────────────┘
```

### Validation Layers

**Layer 1: Schema Validation** (Existing - Pydantic)
- Field types, ranges, required fields
- Basic constraints

**Layer 2: Prompt Linting** (NEW)
- Quality checks on prompts
- High-entropy detection
- Instruction completeness
- Few-shot quality

**Layer 3: Configuration Validation** (NEW)
- Best-practice checks
- Cross-field validation
- Pattern-specific rules

**Layer 4: Behavioral Testing** (NEW)
- Test query execution
- Output validation
- Regression testing

---

## Implementation

### Phase 1: Prompt Linter (2 days)

#### 1.1 Validation Rules Engine

**File:** `src/orchestrator/app/services/validation/validation_engine.py`

```python
"""
Use Case validation engine with extensible rule system.
"""

from enum import Enum
from typing import Any, Callable
from pydantic import BaseModel

class ValidationSeverity(str, Enum):
    ERROR = "error"      # Blocks publish
    WARNING = "warning"  # Review recommended
    INFO = "info"        # Suggestion only

class ValidationIssue(BaseModel):
    rule_id: str
    severity: ValidationSeverity
    message: str
    field: str | None = None
    suggestion: str | None = None
    auto_fix: dict | None = None

class ValidationRule:
    """Base class for validation rules."""

    rule_id: str
    name: str
    description: str
    severity: ValidationSeverity

    def validate(self, use_case: dict) -> list[ValidationIssue]:
        """Run validation and return issues."""
        raise NotImplementedError

class ValidationEngine:
    """Orchestrates validation rules."""

    def __init__(self):
        self.rules: list[ValidationRule] = []
        self.register_default_rules()

    def register_rule(self, rule: ValidationRule):
        """Register a validation rule."""
        self.rules.append(rule)

    def validate_use_case(
        self,
        use_case: dict,
        context: dict | None = None
    ) -> list[ValidationIssue]:
        """
        Run all validation rules against Use Case.

        Args:
            use_case: Use Case configuration
            context: Optional context (user role, environment, etc.)

        Returns:
            List of validation issues
        """
        issues = []

        for rule in self.rules:
            try:
                rule_issues = rule.validate(use_case)
                issues.extend(rule_issues)
            except Exception as e:
                logger.error(f"Validation rule {rule.rule_id} failed: {e}")
                issues.append(ValidationIssue(
                    rule_id=rule.rule_id,
                    severity=ValidationSeverity.ERROR,
                    message=f"Validation rule crashed: {str(e)}"
                ))

        return issues

    def register_default_rules(self):
        """Register built-in validation rules."""
        # Prompt linting rules
        self.register_rule(HighEntropyDetectionRule())
        self.register_rule(EmptySystemPromptRule())
        self.register_rule(MissingDeveloperPromptRule())
        self.register_rule(InsufficientFewShotsRule())
        self.register_rule(VagueInstructionsRule())

        # Configuration rules
        self.register_rule(MaxTokensForPatternRule())
        self.register_rule(ReActWithoutToolStepsRule())
        self.register_rule(StrictOutputWithoutSchemaRule())
        self.register_rule(RAGWithoutCollectionsRule())

        # Best practice rules
        self.register_rule(PublishedWithoutTestingRule())
        self.register_rule(CustomPresetWithoutJustificationRule())
```

#### 1.2 Prompt Linting Rules

**File:** `src/orchestrator/app/services/validation/prompt_rules.py`

```python
"""Prompt linting validation rules."""

class HighEntropyDetectionRule(ValidationRule):
    """Detect high-entropy parameter combinations."""

    rule_id = "high-entropy-trap"
    name = "High-Entropy Parameter Detection"
    description = "Detects dangerous temperature + top_p combinations"
    severity = ValidationSeverity.WARNING

    def validate(self, use_case: dict) -> list[ValidationIssue]:
        issues = []

        gen_params = use_case.get("config_json", {}).get("generation_params", {})

        # Get effective parameters (resolve presets)
        temp = gen_params.get("temperature")
        top_p = gen_params.get("top_p")
        preset = gen_params.get("sampling_preset")

        # If using preset, skip (presets are pre-validated)
        if preset and preset != "custom":
            return issues

        # High-entropy trap: both very high
        if temp and top_p and temp > 0.9 and top_p > 0.97:
            issues.append(ValidationIssue(
                rule_id=self.rule_id,
                severity=ValidationSeverity.WARNING,
                message=(
                    f"High-entropy configuration detected: temperature={temp}, "
                    f"top_p={top_p}. This may cause repetition loops or "
                    f"inconsistent outputs."
                ),
                field="config_json.generation_params",
                suggestion=(
                    "Consider using 'balanced' preset (temp=0.65, top_p=0.95) or "
                    "reduce temperature to < 0.8"
                ),
                auto_fix={
                    "generation_params": {
                        "sampling_preset": "balanced",
                        "temperature": None,
                        "top_p": None
                    }
                }
            ))

        # Low-entropy trap: both very low
        if temp and top_p and temp < 0.1 and top_p < 0.85:
            issues.append(ValidationIssue(
                rule_id=self.rule_id,
                severity=ValidationSeverity.WARNING,
                message=(
                    f"Very low-entropy configuration: temperature={temp}, "
                    f"top_p={top_p}. May produce repetitive outputs."
                ),
                field="config_json.generation_params",
                suggestion="Consider using 'strict' preset (temp=0.15, top_p=0.90)"
            ))

        return issues

class EmptySystemPromptRule(ValidationRule):
    """Check for empty or missing system prompt."""

    rule_id = "empty-system-prompt"
    name = "Empty System Prompt"
    description = "System prompt is required for clear behavior"
    severity = ValidationSeverity.ERROR

    def validate(self, use_case: dict) -> list[ValidationIssue]:
        issues = []

        prompts = use_case.get("metadata_json", {}).get("prompts", {})
        system_prompt = prompts.get("system_prompt", "").strip()

        if not system_prompt:
            issues.append(ValidationIssue(
                rule_id=self.rule_id,
                severity=ValidationSeverity.ERROR,
                message="System prompt is empty. Provide clear role and task instructions.",
                field="metadata_json.prompts.system_prompt",
                suggestion=(
                    "Example: 'You are a cybersecurity analyst specializing in "
                    "threat intelligence triage. Your task is to assess threats "
                    "and provide actionable recommendations.'"
                )
            ))
        elif len(system_prompt) < 50:
            issues.append(ValidationIssue(
                rule_id=self.rule_id,
                severity=ValidationSeverity.WARNING,
                message=(
                    f"System prompt is very short ({len(system_prompt)} chars). "
                    f"Provide more context for better results."
                ),
                field="metadata_json.prompts.system_prompt",
                suggestion="Add role description, task explanation, and expected behavior"
            ))

        return issues

class MissingDeveloperPromptRule(ValidationRule):
    """Check for missing developer prompt in structured outputs."""

    rule_id = "missing-developer-prompt"
    name = "Missing Developer Prompt"
    description = "Developer prompt recommended for JSON/structured outputs"
    severity = ValidationSeverity.WARNING

    def validate(self, use_case: dict) -> list[ValidationIssue]:
        issues = []

        config = use_case.get("config_json", {})
        output_format = config.get("output_contract", {}).get("format")
        prompts = use_case.get("metadata_json", {}).get("prompts", {})
        developer_prompt = prompts.get("developer_prompt", "").strip()

        # If output is JSON/structured and no developer prompt
        if output_format in ["json", "structured"] and not developer_prompt:
            issues.append(ValidationIssue(
                rule_id=self.rule_id,
                severity=ValidationSeverity.WARNING,
                message=(
                    "Developer prompt recommended for structured outputs. "
                    "Use it to specify JSON format, required fields, and citations."
                ),
                field="metadata_json.prompts.developer_prompt",
                suggestion=(
                    "Example: 'Output valid JSON only. Include fields: threat_level, "
                    "confidence, iocs (array). Use [doc_id] format for citations.'"
                )
            ))

        return issues

class InsufficientFewShotsRule(ValidationRule):
    """Check for insufficient few-shot examples."""

    rule_id = "insufficient-few-shots"
    name = "Insufficient Few-Shot Examples"
    description = "Recommend 3-5 few-shot examples for consistent behavior"
    severity = ValidationSeverity.INFO

    def validate(self, use_case: dict) -> list[ValidationIssue]:
        issues = []

        prompts = use_case.get("metadata_json", {}).get("prompts", {})
        fewshots = prompts.get("fewshots", [])

        if len(fewshots) < 3:
            issues.append(ValidationIssue(
                rule_id=self.rule_id,
                severity=ValidationSeverity.INFO,
                message=(
                    f"Only {len(fewshots)} few-shot examples provided. "
                    f"Recommend 3-5 examples for best results."
                ),
                field="metadata_json.prompts.fewshots",
                suggestion=(
                    "Add diverse examples covering: typical case, edge case, "
                    "error handling, and desired output format."
                )
            ))

        return issues

class VagueInstructionsRule(ValidationRule):
    """Detect vague or ambiguous instructions."""

    rule_id = "vague-instructions"
    name = "Vague Instructions"
    description = "Detect prompts lacking specific instructions"
    severity = ValidationSeverity.WARNING

    VAGUE_PHRASES = [
        "help", "assist", "try to", "maybe", "if possible",
        "do your best", "approximately"
    ]

    def validate(self, use_case: dict) -> list[ValidationIssue]:
        issues = []

        prompts = use_case.get("metadata_json", {}).get("prompts", {})
        system_prompt = prompts.get("system_prompt", "").lower()
        developer_prompt = prompts.get("developer_prompt", "").lower()

        combined = system_prompt + " " + developer_prompt

        found_vague = [phrase for phrase in self.VAGUE_PHRASES if phrase in combined]

        if found_vague:
            issues.append(ValidationIssue(
                rule_id=self.rule_id,
                severity=ValidationSeverity.WARNING,
                message=(
                    f"Vague language detected: {', '.join(found_vague)}. "
                    f"Use clear, specific instructions instead."
                ),
                field="metadata_json.prompts",
                suggestion=(
                    "Replace vague phrases with specific instructions. "
                    "Instead of 'try to extract IOCs', use 'extract all IP addresses, "
                    "domains, and hashes from the text.'"
                )
            ))

        return issues
```

#### 1.3 Configuration Validation Rules

**File:** `src/orchestrator/app/services/validation/config_rules.py`

```python
"""Configuration validation rules."""

class MaxTokensForPatternRule(ValidationRule):
    """Validate max_tokens appropriate for pattern."""

    rule_id = "max-tokens-for-pattern"
    name = "Max Tokens for Pattern"
    description = "Check if max_tokens matches pattern requirements"
    severity = ValidationSeverity.WARNING

    PATTERN_RECOMMENDATIONS = {
        "react": 2048,           # ReAct needs room for tool outputs
        "chain-of-thought": 1536,
        "tree-of-thoughts": 3072,
        "zero-shot": 1024,
        "few-shot": 1536
    }

    def validate(self, use_case: dict) -> list[ValidationIssue]:
        issues = []

        # Get pattern ID from metadata
        pattern_id = use_case.get("metadata_json", {}).get("pattern_id")
        if not pattern_id:
            return issues

        # Get max_tokens from config
        gen_params = use_case.get("config_json", {}).get("generation_params", {})
        max_tokens = gen_params.get("max_tokens", 1024)

        # Check recommendation
        recommended = self.PATTERN_RECOMMENDATIONS.get(pattern_id)
        if recommended and max_tokens < recommended:
            issues.append(ValidationIssue(
                rule_id=self.rule_id,
                severity=ValidationSeverity.WARNING,
                message=(
                    f"Pattern '{pattern_id}' recommends max_tokens >= {recommended}, "
                    f"but configured with {max_tokens}. Output may be truncated."
                ),
                field="config_json.generation_params.max_tokens",
                suggestion=f"Increase max_tokens to {recommended} or higher",
                auto_fix={"generation_params": {"max_tokens": recommended}}
            ))

        return issues

class ReActWithoutToolStepsRule(ValidationRule):
    """Check ReAct patterns have max_tool_steps configured."""

    rule_id = "react-without-tool-steps"
    name = "ReAct Without Tool Steps Limit"
    description = "ReAct patterns need max_tool_steps to prevent runaway costs"
    severity = ValidationSeverity.ERROR

    def validate(self, use_case: dict) -> list[ValidationIssue]:
        issues = []

        pattern_id = use_case.get("metadata_json", {}).get("pattern_id", "")
        gen_params = use_case.get("config_json", {}).get("generation_params", {})
        tools_allowlist = use_case.get("config_json", {}).get("tools_allowlist", [])

        # If pattern is ReAct or tools are enabled
        if "react" in pattern_id.lower() or len(tools_allowlist) > 0:
            max_tool_steps = gen_params.get("max_tool_steps")

            if not max_tool_steps:
                issues.append(ValidationIssue(
                    rule_id=self.rule_id,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        "Tool-using patterns must set max_tool_steps to prevent "
                        "runaway costs. Recommended: 5 steps."
                    ),
                    field="config_json.generation_params.max_tool_steps",
                    suggestion="Add max_tool_steps: 5 to generation_params",
                    auto_fix={"generation_params": {"max_tool_steps": 5}}
                ))

        return issues

class StrictOutputWithoutSchemaRule(ValidationRule):
    """Check strict validation has output schema."""

    rule_id = "strict-without-schema"
    name = "Strict Validation Without Schema"
    description = "STRICT validation mode requires output_schema"
    severity = ValidationSeverity.ERROR

    def validate(self, use_case: dict) -> list[ValidationIssue]:
        issues = []

        output_contract = use_case.get("config_json", {}).get("output_contract", {})
        validation_mode = output_contract.get("validation_mode")
        output_schema = output_contract.get("output_schema")

        if validation_mode == "strict" and not output_schema:
            issues.append(ValidationIssue(
                rule_id=self.rule_id,
                severity=ValidationSeverity.ERROR,
                message=(
                    "Output validation mode is STRICT but no output_schema provided. "
                    "Either add schema or use BEST_EFFORT mode."
                ),
                field="config_json.output_contract",
                suggestion="Add output_schema with JSON Schema definition"
            ))

        return issues

class RAGWithoutCollectionsRule(ValidationRule):
    """Check RAG enabled has collections configured."""

    rule_id = "rag-without-collections"
    name = "RAG Without Collections"
    description = "RAG enabled but no collections configured"
    severity = ValidationSeverity.ERROR

    def validate(self, use_case: dict) -> list[ValidationIssue]:
        issues = []

        rag_config = use_case.get("config_json", {}).get("rag", {})
        enabled = rag_config.get("enabled", False)
        collections = rag_config.get("vector_collections", [])

        if enabled and not collections:
            issues.append(ValidationIssue(
                rule_id=self.rule_id,
                severity=ValidationSeverity.ERROR,
                message="RAG is enabled but no vector collections configured",
                field="config_json.rag.vector_collections",
                suggestion="Add at least one collection or disable RAG"
            ))

        return issues
```

#### 1.4 Validation API

**File:** `src/orchestrator/app/routers/use_case_validation.py`

```python
"""Use Case validation endpoints."""

from fastapi import APIRouter, Depends
from ..services.validation.validation_engine import ValidationEngine, ValidationIssue

router = APIRouter(prefix="/api/v1/use-cases", tags=["use-cases"])

@router.post("/{use_case_id}/validate", response_model=ValidationReport)
async def validate_use_case(
    use_case_id: str,
    current_user: TokenPayload = Depends(auth_required)
) -> ValidationReport:
    """
    Validate Use Case configuration and prompts.

    Returns validation report with errors, warnings, and suggestions.
    """
    # Load Use Case
    use_case = await use_case_service.get_by_id(use_case_id)
    if not use_case:
        raise HTTPException(404, "Use Case not found")

    # Run validation
    engine = ValidationEngine()
    issues = engine.validate_use_case(
        use_case=use_case.model_dump(),
        context={"user_role": current_user.role}
    )

    # Group by severity
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    infos = [i for i in issues if i.severity == "info"]

    return ValidationReport(
        use_case_id=use_case_id,
        is_valid=len(errors) == 0,
        can_publish=len(errors) == 0,
        issues=issues,
        errors=errors,
        warnings=warnings,
        infos=infos,
        validated_at=datetime.utcnow()
    )

@router.post("/{use_case_id}/auto-fix", response_model=UseCase)
async def auto_fix_issues(
    use_case_id: str,
    issue_ids: list[str],
    current_user: TokenPayload = Depends(corpus_admin_required)
) -> UseCase:
    """
    Auto-fix validation issues where possible.

    Requires corpus_admin or admin role.
    """
    # Load Use Case
    use_case = await use_case_service.get_by_id(use_case_id)
    if not use_case:
        raise HTTPException(404, "Use Case not found")

    # Get validation issues
    engine = ValidationEngine()
    issues = engine.validate_use_case(use_case.model_dump())

    # Filter to requested issues
    to_fix = [i for i in issues if i.rule_id in issue_ids and i.auto_fix]

    if not to_fix:
        raise HTTPException(400, "No auto-fixable issues found")

    # Apply fixes
    updated_config = use_case.config_json.copy()
    for issue in to_fix:
        # Deep merge auto_fix into config
        updated_config = deep_merge(updated_config, issue.auto_fix)

    # Update Use Case
    use_case.config_json = updated_config
    await use_case_service.update(use_case)

    logger.info(
        f"Auto-fixed {len(to_fix)} issues in Use Case {use_case_id} "
        f"by {current_user.username}"
    )

    return use_case
```

---

### Phase 2: Test Query Interface (1 day)

#### 2.1 Test Execution Service

**File:** `src/orchestrator/app/services/use_case_testing_service.py`

```python
"""Use Case testing service."""

class UseCaseTestingService:
    """Execute test queries against Use Cases."""

    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator

    async def execute_test_query(
        self,
        use_case_id: str,
        test_query: str,
        expected_output: dict | None = None,
        user_id: str | None = None
    ) -> TestQueryResult:
        """
        Execute a test query against Use Case.

        Args:
            use_case_id: Use Case to test
            test_query: Test query text
            expected_output: Optional expected output for validation
            user_id: User executing test

        Returns:
            Test result with response and validation
        """
        start_time = time.time()

        try:
            # Execute query through orchestrator
            response = await self.orchestrator.process_request(
                query=test_query,
                use_case_id=use_case_id,
                user_id=user_id or "test-user",
                request_id=f"test-{uuid.uuid4()}"
            )

            execution_time = time.time() - start_time

            # Validate output if expected provided
            validation_passed = True
            validation_message = None

            if expected_output:
                validation_passed, validation_message = self._validate_output(
                    response,
                    expected_output
                )

            return TestQueryResult(
                success=True,
                query=test_query,
                response=response,
                execution_time_ms=int(execution_time * 1000),
                validation_passed=validation_passed,
                validation_message=validation_message,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Test query failed: {e}", exc_info=True)
            return TestQueryResult(
                success=False,
                query=test_query,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
                timestamp=datetime.utcnow()
            )

    def _validate_output(
        self,
        response: dict,
        expected: dict
    ) -> tuple[bool, str | None]:
        """Validate response against expected output."""
        # Check required fields
        if "required_fields" in expected:
            for field in expected["required_fields"]:
                if field not in response:
                    return False, f"Missing required field: {field}"

        # Check output format
        if "format" in expected:
            actual_format = response.get("format")
            if actual_format != expected["format"]:
                return False, f"Format mismatch: expected {expected['format']}, got {actual_format}"

        # Check schema validation
        if "schema" in expected:
            try:
                jsonschema.validate(response, expected["schema"])
            except jsonschema.ValidationError as e:
                return False, f"Schema validation failed: {e.message}"

        return True, "All validations passed"

    async def run_test_suite(
        self,
        use_case_id: str,
        test_cases: list[TestCase]
    ) -> TestSuiteResult:
        """
        Run a suite of test cases against Use Case.

        Args:
            use_case_id: Use Case to test
            test_cases: List of test cases

        Returns:
            Aggregated test suite results
        """
        results = []

        for test_case in test_cases:
            result = await self.execute_test_query(
                use_case_id=use_case_id,
                test_query=test_case.query,
                expected_output=test_case.expected_output
            )
            results.append(result)

        # Aggregate results
        passed = sum(1 for r in results if r.success and r.validation_passed)
        failed = len(results) - passed
        avg_time = sum(r.execution_time_ms for r in results) / len(results)

        return TestSuiteResult(
            use_case_id=use_case_id,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            pass_rate=passed / len(results) if results else 0,
            avg_execution_time_ms=int(avg_time),
            results=results,
            timestamp=datetime.utcnow()
        )
```

#### 2.2 Frontend Test Query Interface

**File:** `src/app/components/use-case-test-panel/use-case-test-panel.component.ts`

```typescript
@Component({
  selector: 'app-use-case-test-panel',
  template: `
    <mat-card class="test-panel">
      <mat-card-header>
        <mat-card-title>
          <mat-icon>science</mat-icon>
          Test Use Case
        </mat-card-title>
      </mat-card-header>

      <mat-card-content>
        <!-- Test Query Input -->
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Test Query</mat-label>
          <textarea matInput
                    [(ngModel)]="testQuery"
                    placeholder="Enter a test query..."
                    rows="3">
          </textarea>
        </mat-form-field>

        <!-- Expected Output (Optional) -->
        <mat-expansion-panel>
          <mat-expansion-panel-header>
            <mat-panel-title>Expected Output (Optional)</mat-panel-title>
          </mat-expansion-panel-header>
          <mat-form-field appearance="outline" class="full-width">
            <textarea matInput
                      [(ngModel)]="expectedOutputJson"
                      placeholder='{"format": "json", "required_fields": ["threat_level"]}'
                      rows="5">
            </textarea>
          </mat-form-field>
        </mat-expansion-panel>

        <!-- Execute Button -->
        <div class="actions">
          <button mat-raised-button
                  color="primary"
                  (click)="executeTest()"
                  [disabled]="!testQuery || isExecuting">
            <mat-icon>play_arrow</mat-icon>
            Run Test
          </button>

          <button mat-button
                  *ngIf="hasTestSuite"
                  (click)="runTestSuite()">
            <mat-icon>playlist_play</mat-icon>
            Run All Tests
          </button>
        </div>

        <!-- Results -->
        <div *ngIf="testResult" class="test-result">
          <h4>
            <mat-icon [class.success]="testResult.success"
                      [class.error]="!testResult.success">
              {{ testResult.success ? 'check_circle' : 'error' }}
            </mat-icon>
            Test Result
            <span class="execution-time">
              {{ testResult.execution_time_ms }}ms
            </span>
          </h4>

          <!-- Validation Status -->
          <mat-chip-list *ngIf="testResult.validation_passed !== undefined">
            <mat-chip [class.validation-passed]="testResult.validation_passed"
                      [class.validation-failed]="!testResult.validation_passed">
              {{ testResult.validation_passed ? '✓ Validation Passed' : '✗ Validation Failed' }}
            </mat-chip>
          </mat-chip-list>

          <div *ngIf="!testResult.validation_passed" class="validation-message">
            {{ testResult.validation_message }}
          </div>

          <!-- Response Preview -->
          <mat-expansion-panel [expanded]="true">
            <mat-expansion-panel-header>
              <mat-panel-title>Response</mat-panel-title>
            </mat-expansion-panel-header>

            <app-llm-content-renderer
              [content]="testResult.response.answer"
              [format]="testResult.response.format">
            </app-llm-content-renderer>
          </mat-expansion-panel>

          <!-- Full Response JSON -->
          <mat-expansion-panel>
            <mat-expansion-panel-header>
              <mat-panel-title>Full Response JSON</mat-panel-title>
            </mat-expansion-panel-header>
            <pre>{{ testResult.response | json }}</pre>
          </mat-expansion-panel>
        </div>
      </mat-card-content>
    </mat-card>
  `
})
export class UseCaseTestPanelComponent {
  @Input() useCaseId: string;

  testQuery: string = '';
  expectedOutputJson: string = '';
  testResult?: TestQueryResult;
  isExecuting: boolean = false;
  hasTestSuite: boolean = false;

  constructor(
    private useCaseService: UseCaseManagementService,
    private snackBar: MatSnackBar
  ) {}

  async executeTest() {
    if (!this.testQuery) return;

    this.isExecuting = true;

    try {
      // Parse expected output if provided
      let expectedOutput = undefined;
      if (this.expectedOutputJson) {
        try {
          expectedOutput = JSON.parse(this.expectedOutputJson);
        } catch (e) {
          this.snackBar.open('Invalid expected output JSON', 'Close', {duration: 3000});
          return;
        }
      }

      // Execute test
      this.testResult = await this.useCaseService.executeTestQuery(
        this.useCaseId,
        this.testQuery,
        expectedOutput
      );

      // Show notification
      if (this.testResult.success) {
        this.snackBar.open(
          `Test passed in ${this.testResult.execution_time_ms}ms`,
          'Close',
          {duration: 3000}
        );
      } else {
        this.snackBar.open('Test failed', 'Close', {duration: 3000});
      }

    } catch (error) {
      this.snackBar.open(`Test error: ${error}`, 'Close', {duration: 5000});
    } finally {
      this.isExecuting = false;
    }
  }

  async runTestSuite() {
    // Load and run test suite for this Use Case
    // TBD: Implement test suite management
  }
}
```

---

### Phase 3: Automated Testing & Reports (1 day)

#### 3.1 Test Suite Management

**Schema:**

```sql
-- Test suites for Use Cases
CREATE TABLE use_case_test_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    use_case_id VARCHAR(255) REFERENCES use_cases(use_case_id),
    suite_name VARCHAR(255) NOT NULL,
    description TEXT,
    test_cases JSONB NOT NULL,
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Test execution history
CREATE TABLE use_case_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    use_case_id VARCHAR(255) REFERENCES use_cases(use_case_id),
    test_suite_id UUID REFERENCES use_case_test_suites(id),
    result_data JSONB NOT NULL,
    passed INTEGER NOT NULL,
    failed INTEGER NOT NULL,
    pass_rate DECIMAL(5,2) NOT NULL,
    executed_by VARCHAR(255),
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_test_results_use_case ON use_case_test_results(use_case_id);
CREATE INDEX idx_test_results_executed_at ON use_case_test_results(executed_at DESC);
```

#### 3.2 Validation Report Component

**File:** `src/app/components/validation-report/validation-report.component.ts`

```typescript
@Component({
  selector: 'app-validation-report',
  template: `
    <mat-card class="validation-report">
      <mat-card-header>
        <mat-card-title>
          <mat-icon [class.valid]="report.is_valid"
                    [class.invalid]="!report.is_valid">
            {{ report.is_valid ? 'check_circle' : 'error' }}
          </mat-icon>
          Validation Report
        </mat-card-title>
        <span class="validated-time">
          {{ report.validated_at | date:'short' }}
        </span>
      </mat-card-header>

      <mat-card-content>
        <!-- Summary -->
        <div class="validation-summary">
          <mat-chip-list>
            <mat-chip *ngIf="report.errors.length > 0" class="error-chip">
              {{ report.errors.length }} Error(s)
            </mat-chip>
            <mat-chip *ngIf="report.warnings.length > 0" class="warning-chip">
              {{ report.warnings.length }} Warning(s)
            </mat-chip>
            <mat-chip *ngIf="report.infos.length > 0" class="info-chip">
              {{ report.infos.length }} Suggestion(s)
            </mat-chip>
            <mat-chip *ngIf="report.is_valid" class="success-chip">
              ✓ All Checks Passed
            </mat-chip>
          </mat-chip-list>
        </div>

        <!-- Publish Status -->
        <mat-card *ngIf="!report.can_publish" class="publish-blocker">
          <mat-icon>block</mat-icon>
          <strong>Cannot publish:</strong> Fix all errors before publishing
        </mat-card>

        <!-- Issues List -->
        <mat-accordion multi>
          <!-- Errors -->
          <mat-expansion-panel *ngIf="report.errors.length > 0" [expanded]="true">
            <mat-expansion-panel-header>
              <mat-panel-title>
                <mat-icon class="error">error</mat-icon>
                Errors ({{ report.errors.length }})
              </mat-panel-title>
            </mat-expansion-panel-header>

            <mat-list>
              <mat-list-item *ngFor="let issue of report.errors">
                <div class="issue-content">
                  <h4>{{ issue.message }}</h4>
                  <div class="issue-field" *ngIf="issue.field">
                    Field: <code>{{ issue.field }}</code>
                  </div>
                  <div class="issue-suggestion" *ngIf="issue.suggestion">
                    💡 Suggestion: {{ issue.suggestion }}
                  </div>
                  <button mat-button
                          *ngIf="issue.auto_fix"
                          (click)="autoFix(issue)">
                    <mat-icon>auto_fix_high</mat-icon>
                    Auto-Fix
                  </button>
                </div>
              </mat-list-item>
            </mat-list>
          </mat-expansion-panel>

          <!-- Warnings -->
          <mat-expansion-panel *ngIf="report.warnings.length > 0">
            <mat-expansion-panel-header>
              <mat-panel-title>
                <mat-icon class="warning">warning</mat-icon>
                Warnings ({{ report.warnings.length }})
              </mat-panel-title>
            </mat-expansion-panel-header>

            <mat-list>
              <mat-list-item *ngFor="let issue of report.warnings">
                <div class="issue-content">
                  <h4>{{ issue.message }}</h4>
                  <div class="issue-suggestion" *ngIf="issue.suggestion">
                    💡 {{ issue.suggestion }}
                  </div>
                  <button mat-button
                          *ngIf="issue.auto_fix"
                          (click)="autoFix(issue)">
                    <mat-icon>auto_fix_high</mat-icon>
                    Auto-Fix
                  </button>
                </div>
              </mat-list-item>
            </mat-list>
          </mat-expansion-panel>

          <!-- Info -->
          <mat-expansion-panel *ngIf="report.infos.length > 0">
            <mat-expansion-panel-header>
              <mat-panel-title>
                <mat-icon class="info">info</mat-icon>
                Suggestions ({{ report.infos.length }})
              </mat-panel-title>
            </mat-expansion-panel-header>

            <mat-list>
              <mat-list-item *ngFor="let issue of report.infos">
                <div class="issue-content">
                  <h4>{{ issue.message }}</h4>
                  <div *ngIf="issue.suggestion">
                    {{ issue.suggestion }}
                  </div>
                </div>
              </mat-list-item>
            </mat-list>
          </mat-expansion-panel>
        </mat-accordion>
      </mat-card-content>
    </mat-card>
  `
})
export class ValidationReportComponent {
  @Input() report: ValidationReport;
  @Output() autoFixApplied = new EventEmitter<ValidationIssue>();

  autoFix(issue: ValidationIssue) {
    this.autoFixApplied.emit(issue);
  }
}
```

---

## Integration with Use Case Lifecycle

### Save-Time Validation

```typescript
// In use-case-wizard.component.ts
async saveUseCase() {
  // Run validation before saving
  const validationReport = await this.useCaseService.validate(this.useCase.use_case_id);

  if (!validationReport.is_valid) {
    // Show validation report dialog
    const dialogRef = this.dialog.open(ValidationReportDialogComponent, {
      data: { report: validationReport },
      width: '800px'
    });

    const result = await dialogRef.afterClosed().toPromise();

    if (result === 'cancel') {
      return; // User cancelled
    }

    if (result === 'fix') {
      // User wants to fix issues
      this.showValidationPanel = true;
      return;
    }
  }

  // Proceed with save
  await this.useCaseService.update(this.useCase);
}
```

### Publish-Time Validation

```typescript
async publishUseCase() {
  // Validate before publishing
  const validationReport = await this.useCaseService.validate(this.useCase.use_case_id);

  if (!validationReport.can_publish) {
    // Block publish
    this.snackBar.open(
      `Cannot publish: ${validationReport.errors.length} error(s) must be fixed`,
      'View Report',
      {duration: 5000}
    ).onAction().subscribe(() => {
      this.showValidationReport(validationReport);
    });
    return;
  }

  if (validationReport.warnings.length > 0) {
    // Warn but allow publish
    const confirm = await this.confirmDialog.open({
      title: 'Publish with Warnings?',
      message: `There are ${validationReport.warnings.length} warnings. Proceed anyway?`
    }).afterClosed().toPromise();

    if (!confirm) return;
  }

  // Proceed with publish
  await this.useCaseService.changeLifecycleState(
    this.useCase.use_case_id,
    'published'
  );
}
```

---

## Documentation

### User Guide

**File:** `docs/user-guides/use-case-validation.md`

**Contents:**
- Understanding validation errors, warnings, and suggestions
- Using the test query interface
- Creating test suites
- Auto-fixing common issues
- Best practices for validation

### Developer Guide

**File:** `docs/development/guides/creating-validation-rules.md`

**Contents:**
- Validation rule architecture
- Creating custom validation rules
- Testing validation rules
- Rule severity levels
- Auto-fix capabilities

---

## Acceptance Criteria

- [ ] Prompt linter with 8+ validation rules
- [ ] High-entropy trap detection functional
- [ ] Configuration validation rules (max_tokens, tool steps, schema checks)
- [ ] Test query interface in Use Case wizard
- [ ] Validation report component with auto-fix
- [ ] Save-time validation checks
- [ ] Publish-time validation blocks errors
- [ ] Backend validation API endpoints
- [ ] Test suite management (CRUD)
- [ ] Test execution history tracking
- [ ] Frontend validation panel
- [ ] Auto-fix functionality for common issues
- [ ] Performance: < 500ms for full validation
- [ ] Integration tests for all validation rules
- [ ] Documentation complete (user + developer guides)

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **False positives** | Medium | Medium | Configurable rule severity, allow override by admin |
| **Performance** | Low | Low | Cache validation results, async validation |
| **Rule maintenance** | Medium | High | Clear documentation, easy rule addition |
| **User frustration** | High | Medium | Clear error messages, auto-fix where possible |

---

## Future Enhancements (Phase 5+)

1. **ML-Based Validation:** Learn from successful Use Cases
2. **Custom Rule Editor:** Visual rule builder for organizations
3. **Regression Testing:** Auto-run tests on config changes
4. **Performance Benchmarking:** Compare test execution times
5. **A/B Testing:** Compare two Use Case versions
6. **Collaborative Testing:** Share test suites across team

---

## Related Work

- **ADR-023:** Sampling Presets - High-entropy detection
- **P3-F5:** Output Formatting - Schema validation
- **P3-F2:** Use Case Management - Lifecycle integration
- **P4 Security Features:** Audit trail for validation

---

**Status:** ✅ COMPLETED (October 21, 2025)
**Owner:** Project team
**Actual Completion:** 1 day
**Completed:** October 21, 2025 (Phase 4 Week 1)
**Priority:** High (Must-complete from Phase 3)
**Session Log:** [2025-10-21-p3-f6-validation-testing-complete.md](../../sessions/2025-10-21-p3-f6-validation-testing-complete.md)
