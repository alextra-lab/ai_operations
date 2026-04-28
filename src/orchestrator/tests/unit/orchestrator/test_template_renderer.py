"""Unit tests for user prompt template renderer."""

import pytest

from src.orchestrator.app.orchestrator.template_renderer import (
    extract_template_variables,
    render_user_prompt_template,
    validate_template_variables,
)


class TestRenderUserPromptTemplate:
    """Tests for render_user_prompt_template."""

    def test_substitutes_all_variables(self):
        out = render_user_prompt_template(
            "Analyze {{incident_id}} with {{severity}}.",
            {"incident_id": "INC-123", "severity": "high"},
            fallback_mode="concatenate",
        )
        assert out == "Analyze INC-123 with high."

    def test_concatenate_mode_missing_var(self):
        out = render_user_prompt_template(
            "ID: {{incident_id}}, Severity: {{severity}}",
            {"incident_id": "INC-1"},
            fallback_mode="concatenate",
        )
        assert out == "ID: INC-1, Severity: [severity: not provided]"

    def test_error_mode_missing_var_raises(self):
        with pytest.raises(ValueError, match="Missing required variable: severity"):
            render_user_prompt_template(
                "ID: {{incident_id}}, Severity: {{severity}}",
                {"incident_id": "INC-1"},
                fallback_mode="error",
            )

    def test_empty_inputs_concatenate(self):
        out = render_user_prompt_template(
            "{{a}} and {{b}}",
            {},
            fallback_mode="concatenate",
        )
        assert out == "[a: not provided] and [b: not provided]"

    def test_empty_inputs_error_raises(self):
        with pytest.raises(ValueError, match="Missing required variable: a"):
            render_user_prompt_template(
                "{{a}} and {{b}}",
                {},
                fallback_mode="error",
            )

    def test_no_placeholders_returns_unchanged(self):
        out = render_user_prompt_template(
            "No variables here.",
            {"x": "y"},
            fallback_mode="concatenate",
        )
        assert out == "No variables here."

    def test_non_string_value_converted(self):
        out = render_user_prompt_template(
            "Count: {{n}}",
            {"n": 42},
            fallback_mode="concatenate",
        )
        assert out == "Count: 42"


class TestExtractTemplateVariables:
    """Tests for extract_template_variables."""

    def test_extracts_unique_names(self):
        assert set(extract_template_variables("{{a}} x {{b}} {{a}}")) == {"a", "b"}

    def test_empty_string(self):
        assert extract_template_variables("") == []

    def test_no_placeholders(self):
        assert extract_template_variables("plain text") == []

    def test_single_placeholder(self):
        assert extract_template_variables("{{only}}") == ["only"]


class TestValidateTemplateVariables:
    """Tests for validate_template_variables."""

    def test_matched_and_unmatched(self):
        template = "{{incident_id}} and {{unknown}}"
        fields = [{"name": "incident_id"}, {"name": "severity"}]
        matched, unmatched = validate_template_variables(template, fields)
        assert set(matched) == {"incident_id"}
        assert set(unmatched) == {"unknown"}

    def test_all_matched(self):
        template = "{{a}} {{b}}"
        fields = [{"name": "a"}, {"name": "b"}]
        matched, unmatched = validate_template_variables(template, fields)
        assert set(matched) == {"a", "b"}
        assert unmatched == []

    def test_empty_fields_ignores_missing_name(self):
        template = "{{x}}"
        fields = [{}]
        matched, unmatched = validate_template_variables(template, fields)
        assert matched == []
        assert unmatched == ["x"]
