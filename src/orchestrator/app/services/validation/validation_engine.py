"""
Use Case validation engine with extensible rule system.

Provides validation for Use Case prompts, configuration, and structure
to ensure quality and consistency before deployment.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from shared.logging_utils.fastapi import get_logger

logger = get_logger(__name__)


class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""

    ERROR = "error"  # Blocks publish
    WARNING = "warning"  # Review recommended
    INFO = "info"  # Suggestion only


class ValidationIssue(BaseModel):
    """Individual validation issue."""

    rule_id: str = Field(..., description="Unique rule identifier")
    severity: ValidationSeverity = Field(..., description="Issue severity")
    message: str = Field(..., description="Human-readable error message")
    field: str | None = Field(
        None, description="Field path (e.g., 'config_json.generation_params')"
    )
    suggestion: str | None = Field(None, description="Suggested fix")
    auto_fix: dict[str, Any] | None = Field(None, description="Auto-fix payload")


class ValidationReport(BaseModel):
    """Aggregated validation report."""

    use_case_id: str = Field(..., description="Use Case ID")
    is_valid: bool = Field(..., description="All validation passed")
    can_publish: bool = Field(..., description="No blocking errors")
    issues: list[ValidationIssue] = Field(default_factory=list, description="All issues")
    errors: list[ValidationIssue] = Field(default_factory=list, description="Error issues")
    warnings: list[ValidationIssue] = Field(default_factory=list, description="Warning issues")
    infos: list[ValidationIssue] = Field(default_factory=list, description="Info issues")
    validated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Validation timestamp"
    )


class ValidationRule:
    """Base class for validation rules."""

    rule_id: str = ""
    name: str = ""
    description: str = ""
    severity: ValidationSeverity = ValidationSeverity.WARNING

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """
        Run validation and return issues.

        Args:
            use_case: Use Case configuration dictionary

        Returns:
            List of validation issues
        """
        raise NotImplementedError(f"Validation rule {self.rule_id} must implement validate()")


class ValidationEngine:
    """Orchestrates validation rules."""

    def __init__(self) -> None:
        self.rules: list[ValidationRule] = []
        self._register_default_rules()

    def register_rule(self, rule: ValidationRule) -> None:  # type: ignore[type-arg]
        """
        Register a validation rule.

        Args:
            rule: ValidationRule instance
        """
        self.rules.append(rule)
        logger.debug(f"Registered validation rule: {rule.rule_id}")

    def validate_use_case(
        self, use_case: dict[str, Any], _context: dict[str, Any] | None = None
    ) -> ValidationReport:
        """
        Run all validation rules against Use Case.

        Args:
            use_case: Use Case configuration
            context: Optional context (user role, environment, etc.)

        Returns:
            Validation report with all issues
        """
        use_case_id = use_case.get("use_case_id", "unknown")
        all_issues: list[ValidationIssue] = []

        logger.info(f"Validating Use Case {use_case_id} with {len(self.rules)} rules")

        for rule in self.rules:
            try:
                rule_issues = rule.validate(use_case)
                all_issues.extend(rule_issues)
                if rule_issues:
                    logger.debug(
                        f"Rule {rule.rule_id} found {len(rule_issues)} issue(s) "
                        f"for Use Case {use_case_id}"
                    )
            except Exception as e:
                logger.error(f"Validation rule {rule.rule_id} failed: {e}", exc_info=True)
                all_issues.append(
                    ValidationIssue(
                        rule_id=rule.rule_id,
                        severity=ValidationSeverity.ERROR,
                        message=f"Validation rule crashed: {e!s}",
                        field=None,
                        suggestion=None,
                        auto_fix=None,
                    )
                )

        # Group by severity
        errors = [i for i in all_issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in all_issues if i.severity == ValidationSeverity.WARNING]
        infos = [i for i in all_issues if i.severity == ValidationSeverity.INFO]

        logger.info(
            f"Validation complete for {use_case_id}: "
            f"{len(errors)} errors, {len(warnings)} warnings, {len(infos)} suggestions"
        )

        return ValidationReport(
            use_case_id=use_case_id,
            is_valid=len(errors) == 0,
            can_publish=len(errors) == 0,
            issues=all_issues,
            errors=errors,
            warnings=warnings,
            infos=infos,
            validated_at=datetime.utcnow(),
        )

    def _register_default_rules(self) -> None:
        """Register built-in validation rules."""
        # Import here to avoid circular dependencies
        from .config_rules import (
            MaxTokensForPatternRule,
            RAGWithoutCollectionsRule,
            ReActWithoutToolStepsRule,
            StrictOutputWithoutSchemaRule,
        )
        from .prompt_rules import (
            EmptySystemPromptRule,
            HighEntropyDetectionRule,
            InsufficientFewShotsRule,
            MissingDeveloperPromptRule,
            VagueInstructionsRule,
        )

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

        logger.info(f"Registered {len(self.rules)} default validation rules")
