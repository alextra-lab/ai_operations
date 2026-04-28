"""Configuration validation rules."""

from typing import Any, ClassVar

from shared.logging_utils.fastapi import get_logger

from .validation_engine import ValidationIssue, ValidationRule, ValidationSeverity

logger = get_logger(__name__)


class MaxTokensForPatternRule(ValidationRule):
    """Validate max_tokens appropriate for pattern."""

    rule_id = "max-tokens-for-pattern"
    name = "Max Tokens for Pattern"
    description = "Check if max_tokens matches pattern requirements"
    severity = ValidationSeverity.WARNING

    PATTERN_RECOMMENDATIONS: ClassVar[dict[str, int]] = {
        "react": 2048,  # ReAct needs room for tool outputs
        "chain-of-thought": 1536,
        "tree-of-thoughts": 3072,
        "zero-shot": 1024,
        "few-shot": 1536,
    }

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """Validate max_tokens for pattern type."""
        issues: list[ValidationIssue] = []

        # Get pattern ID from metadata
        metadata_json = use_case.get("metadata_json", {})
        pattern_id = metadata_json.get("pattern_id")
        if not pattern_id:
            return issues

        # Get max_tokens from config
        config_json = use_case.get("config_json", {})
        gen_params = config_json.get("generation_params", {})
        max_tokens = gen_params.get("max_tokens", 1024)

        # Check recommendation
        recommended = self.PATTERN_RECOMMENDATIONS.get(pattern_id)
        if recommended and max_tokens < recommended:
            issues.append(
                ValidationIssue(
                    rule_id=self.rule_id,
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"Pattern '{pattern_id}' recommends max_tokens >= {recommended}, "
                        f"but configured with {max_tokens}. Output may be truncated."
                    ),
                    field="config_json.generation_params.max_tokens",
                    suggestion=f"Increase max_tokens to {recommended} or higher",
                    auto_fix={"generation_params": {"max_tokens": recommended}},
                )
            )

        return issues


class ReActWithoutToolStepsRule(ValidationRule):
    """Check ReAct patterns have max_tool_steps configured."""

    rule_id = "react-without-tool-steps"
    name = "ReAct Without Tool Steps Limit"
    description = "ReAct patterns need max_tool_steps to prevent runaway costs"
    severity = ValidationSeverity.ERROR

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """Validate tool-using patterns have max_tool_steps."""
        issues: list[ValidationIssue] = []

        metadata_json = use_case.get("metadata_json", {})
        pattern_id = metadata_json.get("pattern_id", "")

        config_json = use_case.get("config_json", {})
        gen_params = config_json.get("generation_params", {})
        tools_allowlist = config_json.get("tools_allowlist", [])

        # If pattern is ReAct or tools are enabled
        if "react" in pattern_id.lower() or len(tools_allowlist) > 0:
            max_tool_steps = gen_params.get("max_tool_steps")

            if not max_tool_steps:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=ValidationSeverity.ERROR,
                        message=(
                            "Tool-using patterns must set max_tool_steps to prevent "
                            "runaway costs. Recommended: 5 steps."
                        ),
                        field="config_json.generation_params.max_tool_steps",
                        suggestion="Add max_tool_steps: 5 to generation_params",
                        auto_fix={"generation_params": {"max_tool_steps": 5}},
                    )
                )

        return issues


class StrictOutputWithoutSchemaRule(ValidationRule):
    """Check strict validation has output schema."""

    rule_id = "strict-without-schema"
    name = "Strict Validation Without Schema"
    description = "STRICT validation mode requires output_schema"
    severity = ValidationSeverity.ERROR

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """Validate STRICT mode has schema."""
        issues: list[ValidationIssue] = []

        config_json = use_case.get("config_json", {})
        output_contract = config_json.get("output_contract", {})
        validation_mode = output_contract.get("validation_mode")
        output_schema = output_contract.get("output_schema")

        if validation_mode == "strict" and not output_schema:
            issues.append(
                ValidationIssue(
                    rule_id=self.rule_id,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        "Output validation mode is STRICT but no output_schema provided. "
                        "Either add schema or use BEST_EFFORT mode."
                    ),
                    field="config_json.output_contract",
                    suggestion="Add output_schema with JSON Schema definition",
                    auto_fix=None,
                )
            )

        return issues


class RAGWithoutCollectionsRule(ValidationRule):
    """Check RAG enabled has collections configured."""

    rule_id = "rag-without-collections"
    name = "RAG Without Collections"
    description = "RAG enabled but no collections configured"
    severity = ValidationSeverity.ERROR

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """Validate RAG configuration has collections."""
        issues: list[ValidationIssue] = []

        config_json = use_case.get("config_json", {})
        rag_config = config_json.get("rag", {})
        enabled = rag_config.get("enabled", False)
        collections = rag_config.get("vector_collections", [])

        if enabled and not collections:
            issues.append(
                ValidationIssue(
                    rule_id=self.rule_id,
                    severity=ValidationSeverity.ERROR,
                    message="RAG is enabled but no vector collections configured",
                    field="config_json.rag.vector_collections",
                    suggestion="Add at least one collection or disable RAG",
                    auto_fix=None,
                )
            )

        return issues
