"""Prompt linting validation rules."""

from typing import Any, ClassVar

from shared.logging_utils.fastapi import get_logger

from .validation_engine import ValidationIssue, ValidationRule, ValidationSeverity

logger = get_logger(__name__)


class HighEntropyDetectionRule(ValidationRule):
    """Detect high-entropy parameter combinations that may cause issues."""

    rule_id = "high-entropy-trap"
    name = "High-Entropy Parameter Detection"
    description = "Detects dangerous temperature + top_p combinations"
    severity = ValidationSeverity.WARNING

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """Validate generation parameters for high-entropy traps."""
        issues: list[ValidationIssue] = []

        config_json = use_case.get("config_json", {})
        gen_params = config_json.get("generation_params", {})

        # Get parameters
        temp = gen_params.get("temperature")
        top_p = gen_params.get("top_p")
        preset = gen_params.get("sampling_preset")

        # If using preset (not custom), skip - presets are pre-validated
        if preset and preset != "custom":
            return issues

        # High-entropy trap: both very high
        if temp is not None and top_p is not None:
            if temp > 0.9 and top_p > 0.97:
                issues.append(
                    ValidationIssue(
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
                                "top_p": None,
                            }
                        },
                    )
                )

            # Low-entropy trap: both very low
            elif temp < 0.1 and top_p < 0.85:
                issues.append(
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=ValidationSeverity.WARNING,
                        message=(
                            f"Very low-entropy configuration: temperature={temp}, "
                            f"top_p={top_p}. May produce repetitive outputs."
                        ),
                        field="config_json.generation_params",
                        suggestion="Consider using 'strict' preset (temp=0.15, top_p=0.90)",
                        auto_fix={
                            "generation_params": {
                                "sampling_preset": "strict",
                                "temperature": None,
                                "top_p": None,
                            }
                        },
                    )
                )

        return issues


class EmptySystemPromptRule(ValidationRule):
    """Check for empty or missing system prompt."""

    rule_id = "empty-system-prompt"
    name = "Empty System Prompt"
    description = "System prompt is required for clear behavior"
    severity = ValidationSeverity.ERROR

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """Validate system prompt is present and meaningful."""
        issues: list[ValidationIssue] = []

        metadata_json = use_case.get("metadata_json", {})
        prompts = metadata_json.get("prompts", {})
        system_prompt = prompts.get("system_prompt", "").strip()

        if not system_prompt:
            issues.append(
                ValidationIssue(
                    rule_id=self.rule_id,
                    severity=ValidationSeverity.ERROR,
                    message="System prompt is empty. Provide clear role and task instructions.",
                    field="metadata_json.prompts.system_prompt",
                    suggestion=(
                        "Example: 'You are a cybersecurity analyst specializing in "
                        "threat intelligence triage. Your task is to assess threats "
                        "and provide actionable recommendations.'"
                    ),
                    auto_fix=None,
                )
            )
        elif len(system_prompt) < 50:
            issues.append(
                ValidationIssue(
                    rule_id=self.rule_id,
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"System prompt is very short ({len(system_prompt)} chars). "
                        f"Provide more context for better results."
                    ),
                    field="metadata_json.prompts.system_prompt",
                    suggestion="Add role description, task explanation, and expected behavior",
                    auto_fix=None,
                )
            )

        return issues


class MissingDeveloperPromptRule(ValidationRule):
    """Check for missing developer prompt in structured outputs."""

    rule_id = "missing-developer-prompt"
    name = "Missing Developer Prompt"
    description = "Developer prompt recommended for JSON/structured outputs"
    severity = ValidationSeverity.WARNING

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """Validate developer prompt for structured outputs."""
        issues: list[ValidationIssue] = []

        config_json = use_case.get("config_json", {})
        output_contract = config_json.get("output_contract", {})
        output_format = output_contract.get("format")

        metadata_json = use_case.get("metadata_json", {})
        prompts = metadata_json.get("prompts", {})
        developer_prompt = prompts.get("developer_prompt", "").strip()

        # If output is JSON/structured and no developer prompt
        if output_format in ["json", "structured"] and not developer_prompt:
            issues.append(
                ValidationIssue(
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
                    ),
                    auto_fix=None,
                )
            )

        return issues


class InsufficientFewShotsRule(ValidationRule):
    """Check for insufficient few-shot examples."""

    rule_id = "insufficient-few-shots"
    name = "Insufficient Few-Shot Examples"
    description = "Recommend 3-5 few-shot examples for consistent behavior"
    severity = ValidationSeverity.INFO

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """Validate few-shot examples count."""
        issues: list[ValidationIssue] = []

        metadata_json = use_case.get("metadata_json", {})
        prompts = metadata_json.get("prompts", {})
        fewshots = prompts.get("fewshots", [])

        if len(fewshots) < 3:
            issues.append(
                ValidationIssue(
                    rule_id=self.rule_id,
                    severity=ValidationSeverity.INFO,
                    message=(
                        f"Only {len(fewshots)} few-shot example(s) provided. "
                        f"Recommend 3-5 examples for best results."
                    ),
                    field="metadata_json.prompts.fewshots",
                    suggestion=(
                        "Add diverse examples covering: typical case, edge case, "
                        "error handling, and desired output format."
                    ),
                    auto_fix=None,
                )
            )

        return issues


class VagueInstructionsRule(ValidationRule):
    """Detect vague or ambiguous instructions."""

    rule_id = "vague-instructions"
    name = "Vague Instructions"
    description = "Detect prompts lacking specific instructions"
    severity = ValidationSeverity.WARNING

    VAGUE_PHRASES: ClassVar[list[str]] = [
        "help",
        "assist",
        "try to",
        "maybe",
        "if possible",
        "do your best",
        "approximately",
    ]

    def validate(self, use_case: dict[str, Any]) -> list[ValidationIssue]:
        """Validate prompts for vague language."""
        issues: list[ValidationIssue] = []

        metadata_json = use_case.get("metadata_json", {})
        prompts = metadata_json.get("prompts", {})
        system_prompt = prompts.get("system_prompt", "").lower()
        developer_prompt = prompts.get("developer_prompt", "").lower()

        combined = system_prompt + " " + developer_prompt

        found_vague = [phrase for phrase in self.VAGUE_PHRASES if phrase in combined]

        if found_vague:
            issues.append(
                ValidationIssue(
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
                    ),
                    auto_fix=None,
                )
            )

        return issues
