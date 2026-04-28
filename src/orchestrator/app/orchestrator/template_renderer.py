"""
User prompt template rendering for use case execution.

Renders a template string with {{variable}} placeholders by substituting
input field values. Used when use_case_config.user_prompt_template is set;
otherwise the orchestrator uses legacy "field: value" concatenation.
"""

import re
from typing import Any

VARIABLE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def render_user_prompt_template(
    template: str,
    inputs: dict[str, Any],
    fallback_mode: str = "concatenate",
) -> str:
    """
    Render user prompt template with input values.

    Args:
        template: Template string with {{variable}} placeholders.
        inputs: Dictionary of input field names to values.
        fallback_mode: "concatenate" (leave placeholder text for missing vars)
            or "error" (raise ValueError if a variable is missing).

    Returns:
        Rendered template string.

    Raises:
        ValueError: If fallback_mode is "error" and a variable is missing
            from inputs.
    """

    def replace_variable(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name in inputs:
            return str(inputs[var_name])
        if fallback_mode == "error":
            raise ValueError(f"Missing required variable: {var_name}")
        return f"[{var_name}: not provided]"

    return VARIABLE_PATTERN.sub(replace_variable, template)


def extract_template_variables(template: str) -> list[str]:
    """Extract all {{variable}} names from a template (unique, order not guaranteed)."""
    return list(set(VARIABLE_PATTERN.findall(template)))


def validate_template_variables(
    template: str,
    input_fields: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """
    Validate that template variables match input field names.

    Args:
        template: Template string with {{variable}} placeholders.
        input_fields: List of input field dicts with at least a "name" key.

    Returns:
        Tuple of (matched_vars, unmatched_vars). Unmatched vars appear in
        the template but are not in input_fields (may indicate a typo).
    """
    template_vars = set(extract_template_variables(template))
    field_names = {f.get("name") for f in input_fields if f.get("name")}
    matched = list(template_vars & field_names)
    unmatched = list(template_vars - field_names)
    return matched, unmatched
