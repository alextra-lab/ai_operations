"""
Unit tests for prompt linting validation rules.
"""

from src.orchestrator.app.services.validation import ValidationSeverity
from src.orchestrator.app.services.validation.prompt_rules import (
    EmptySystemPromptRule,
    HighEntropyDetectionRule,
    InsufficientFewShotsRule,
    MissingDeveloperPromptRule,
    VagueInstructionsRule,
)


class TestHighEntropyDetectionRule:
    """Tests for HighEntropyDetectionRule."""

    def test_high_entropy_trap(self):
        """Test detection of high-entropy parameter combination."""
        rule = HighEntropyDetectionRule()
        use_case = {
            "config_json": {
                "generation_params": {
                    "sampling_preset": "custom",
                    "temperature": 0.95,
                    "top_p": 0.99,
                }
            }
        }

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.WARNING
        assert "high-entropy" in issues[0].message.lower()
        assert issues[0].auto_fix is not None

    def test_low_entropy_trap(self):
        """Test detection of low-entropy parameter combination."""
        rule = HighEntropyDetectionRule()
        use_case = {
            "config_json": {
                "generation_params": {
                    "sampling_preset": "custom",
                    "temperature": 0.05,
                    "top_p": 0.80,
                }
            }
        }

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.WARNING
        assert "low-entropy" in issues[0].message.lower()

    def test_preset_skips_validation(self):
        """Test that preset usage skips validation."""
        rule = HighEntropyDetectionRule()
        use_case = {
            "config_json": {
                "generation_params": {
                    "sampling_preset": "balanced",
                    # These would trigger validation if custom
                    "temperature": 0.95,
                    "top_p": 0.99,
                }
            }
        }

        issues = rule.validate(use_case)

        # Should not trigger because using preset
        assert len(issues) == 0

    def test_balanced_parameters(self):
        """Test that balanced parameters pass validation."""
        rule = HighEntropyDetectionRule()
        use_case = {
            "config_json": {
                "generation_params": {
                    "sampling_preset": "custom",
                    "temperature": 0.7,
                    "top_p": 0.95,
                }
            }
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0


class TestEmptySystemPromptRule:
    """Tests for EmptySystemPromptRule."""

    def test_empty_prompt(self):
        """Test detection of empty system prompt."""
        rule = EmptySystemPromptRule()
        use_case = {"metadata_json": {"prompts": {"system_prompt": ""}}}

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.ERROR
        assert "empty" in issues[0].message.lower()

    def test_short_prompt(self):
        """Test detection of very short system prompt."""
        rule = EmptySystemPromptRule()
        use_case = {"metadata_json": {"prompts": {"system_prompt": "Short."}}}

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.WARNING
        assert "short" in issues[0].message.lower()

    def test_valid_prompt(self):
        """Test that sufficiently long prompt passes."""
        rule = EmptySystemPromptRule()
        use_case = {
            "metadata_json": {
                "prompts": {
                    "system_prompt": "You are a cybersecurity analyst specialized in threat intelligence triage. Your task is to assess threats and provide recommendations."
                }
            }
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0


class TestMissingDeveloperPromptRule:
    """Tests for MissingDeveloperPromptRule."""

    def test_missing_for_json_output(self):
        """Test detection of missing developer prompt for JSON output."""
        rule = MissingDeveloperPromptRule()
        use_case = {
            "config_json": {"output_contract": {"format": "json"}},
            "metadata_json": {"prompts": {"developer_prompt": ""}},
        }

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.WARNING
        assert "developer prompt" in issues[0].message.lower()

    def test_not_required_for_text_output(self):
        """Test that developer prompt not required for text output."""
        rule = MissingDeveloperPromptRule()
        use_case = {
            "config_json": {"output_contract": {"format": "text"}},
            "metadata_json": {"prompts": {"developer_prompt": ""}},
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0


class TestInsufficientFewShotsRule:
    """Tests for InsufficientFewShotsRule."""

    def test_no_fewshots(self):
        """Test detection of missing few-shot examples."""
        rule = InsufficientFewShotsRule()
        use_case = {"metadata_json": {"prompts": {"fewshots": []}}}

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.INFO
        assert "0 few-shot" in issues[0].message

    def test_insufficient_fewshots(self):
        """Test detection of insufficient few-shot examples."""
        rule = InsufficientFewShotsRule()
        use_case = {
            "metadata_json": {"prompts": {"fewshots": [{"input": "test", "output": "result"}]}}
        }

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert "1 few-shot" in issues[0].message

    def test_sufficient_fewshots(self):
        """Test that 3+ few-shots pass validation."""
        rule = InsufficientFewShotsRule()
        use_case = {
            "metadata_json": {
                "prompts": {
                    "fewshots": [
                        {"input": "test1", "output": "result1"},
                        {"input": "test2", "output": "result2"},
                        {"input": "test3", "output": "result3"},
                    ]
                }
            }
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0


class TestVagueInstructionsRule:
    """Tests for VagueInstructionsRule."""

    def test_vague_language_detection(self):
        """Test detection of vague language in prompts."""
        rule = VagueInstructionsRule()
        use_case = {
            "metadata_json": {
                "prompts": {
                    "system_prompt": "Please help analyze the threat",
                    "developer_prompt": "Try to extract IOCs if possible",
                }
            }
        }

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.WARNING
        assert "vague language" in issues[0].message.lower()
        # Should detect "help", "try to", "if possible"
        assert any(phrase in issues[0].message for phrase in ["help", "try to", "if possible"])

    def test_clear_instructions(self):
        """Test that clear instructions pass validation."""
        rule = VagueInstructionsRule()
        use_case = {
            "metadata_json": {
                "prompts": {
                    "system_prompt": "You are a threat analyst. Extract all IOCs from the input.",
                    "developer_prompt": "Output JSON with fields: ip_addresses, domains, hashes",
                }
            }
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0
