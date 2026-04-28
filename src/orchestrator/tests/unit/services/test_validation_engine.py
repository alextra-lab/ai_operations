"""
Unit tests for ValidationEngine.
"""

import pytest

from src.orchestrator.app.services.validation import (
    ValidationEngine,
    ValidationIssue,
    ValidationReport,
    ValidationRule,
    ValidationSeverity,
)


@pytest.fixture
def validation_engine():
    """Fixture for ValidationEngine instance."""
    return ValidationEngine()


@pytest.fixture
def sample_use_case():
    """Sample Use Case for testing."""
    return {
        "use_case_id": "test-001",
        "config_json": {
            "generation_params": {
                "sampling_preset": "balanced",
                "temperature": 0.65,
                "top_p": 0.95,
                "max_tokens": 1024,
            },
            "output_contract": {
                "format": "text",
                "validation_mode": "best_effort",
            },
            "rag": {
                "enabled": False,
                "vector_collections": [],
            },
            "tools_allowlist": [],
        },
        "metadata_json": {
            "prompts": {
                "system_prompt": "You are a cybersecurity analyst specialized in threat intelligence triage. Your task is to assess threats and provide recommendations.",
                "developer_prompt": "",
                "fewshots": [],
            },
            "pattern_id": "zero-shot",
        },
    }


class TestValidationEngine:
    """Tests for ValidationEngine."""

    def test_engine_initialization(self, validation_engine):
        """Test that engine initializes with default rules."""
        assert len(validation_engine.rules) == 9  # 5 prompt + 4 config rules

    def test_validate_valid_use_case(self, validation_engine, sample_use_case):
        """Test validation of a valid Use Case."""
        report = validation_engine.validate_use_case(sample_use_case)

        assert isinstance(report, ValidationReport)
        assert report.use_case_id == "test-001"
        assert report.is_valid
        assert report.can_publish
        # May have warnings/info but no errors
        assert len(report.errors) == 0

    def test_validate_use_case_with_errors(self, validation_engine):
        """Test validation with errors (empty system prompt)."""
        use_case = {
            "use_case_id": "test-002",
            "config_json": {"generation_params": {}, "output_contract": {}},
            "metadata_json": {"prompts": {"system_prompt": ""}},
        }

        report = validation_engine.validate_use_case(use_case)

        assert not report.is_valid
        assert not report.can_publish
        assert len(report.errors) > 0
        assert any(i.rule_id == "empty-system-prompt" for i in report.errors)

    def test_validate_use_case_with_warnings(self, validation_engine):
        """Test validation with warnings (short system prompt)."""
        use_case = {
            "use_case_id": "test-003",
            "config_json": {"generation_params": {}, "output_contract": {}},
            "metadata_json": {"prompts": {"system_prompt": "Short"}},
        }

        report = validation_engine.validate_use_case(use_case)

        # Valid but has warnings
        assert report.is_valid  # No errors
        assert report.can_publish
        assert len(report.warnings) > 0
        assert any(i.rule_id == "empty-system-prompt" for i in report.warnings)

    def test_register_custom_rule(self, validation_engine):
        """Test registering a custom validation rule."""

        class CustomRule(ValidationRule):
            rule_id = "custom-test-rule"
            name = "Custom Test Rule"
            description = "Test rule"
            severity = ValidationSeverity.INFO

            def validate(self, use_case):
                return [
                    ValidationIssue(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        message="Custom validation message",
                    )
                ]

        initial_count = len(validation_engine.rules)
        validation_engine.register_rule(CustomRule())
        assert len(validation_engine.rules) == initial_count + 1

    def test_validation_context(self, validation_engine, sample_use_case):
        """Test validation with context."""
        context = {"user_role": "admin", "environment": "production"}
        report = validation_engine.validate_use_case(sample_use_case, context=context)

        assert isinstance(report, ValidationReport)
        assert report.use_case_id == "test-001"

    def test_validation_issue_grouping(self, validation_engine):
        """Test that issues are properly grouped by severity."""
        use_case = {
            "use_case_id": "test-004",
            "config_json": {
                "generation_params": {"temperature": 0.95, "top_p": 0.99},
                "output_contract": {},
            },
            "metadata_json": {
                "prompts": {
                    "system_prompt": "",  # Error
                    "fewshots": [],  # Info
                }
            },
        }

        report = validation_engine.validate_use_case(use_case)

        # Should have errors, warnings, and infos
        assert len(report.errors) > 0
        assert len(report.warnings) > 0
        assert len(report.infos) > 0

        # All issues should be in main list
        total_issues = len(report.errors) + len(report.warnings) + len(report.infos)
        assert len(report.issues) == total_issues
