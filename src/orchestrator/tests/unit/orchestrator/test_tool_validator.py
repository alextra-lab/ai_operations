"""
Unit tests for Tool Validator.

Tests the tool validation logic against allowlists.
"""

import pytest

from src.orchestrator.app.orchestrator.tool_registry import (
    ToolCategory,
    ToolMetadata,
    ToolRegistry,
)
from src.orchestrator.app.orchestrator.tool_validator import (
    ToolCallValidationError,
    ToolValidator,
)


def test_validator_initialization():
    """Test that validator initializes correctly."""
    validator = ToolValidator()
    assert validator.registry is not None


def test_validator_with_custom_registry():
    """Test validator with custom registry."""
    registry = ToolRegistry()
    validator = ToolValidator(registry=registry)
    assert validator.registry is registry


def test_validate_tool_with_empty_allowlist():
    """Test that empty allowlist allows all tools."""
    validator = ToolValidator()

    # Empty allowlist should allow any tool
    assert validator.validate_tool_call("any_tool", []) is True
    assert validator.validate_tool_call("web_search", []) is True
    assert validator.validate_tool_call("code_interpreter", []) is True


def test_validate_tool_allowed():
    """Test that tool in allowlist is allowed."""
    validator = ToolValidator()

    allowlist = ["web_search", "code_interpreter"]

    assert validator.validate_tool_call("web_search", allowlist) is True
    assert validator.validate_tool_call("code_interpreter", allowlist) is True


def test_validate_tool_blocked():
    """Test that tool not in allowlist is blocked."""
    validator = ToolValidator()

    allowlist = ["web_search"]

    assert validator.validate_tool_call("code_interpreter", allowlist) is False
    assert validator.validate_tool_call("data_analysis", allowlist) is False


def test_validate_tool_case_sensitive():
    """Test that tool name matching is case-sensitive."""
    validator = ToolValidator()

    allowlist = ["web_search"]

    assert validator.validate_tool_call("web_search", allowlist) is True
    assert validator.validate_tool_call("Web_Search", allowlist) is False
    assert validator.validate_tool_call("WEB_SEARCH", allowlist) is False


def test_validate_multiple_tools():
    """Test validating multiple tools at once."""
    validator = ToolValidator()

    allowlist = ["web_search", "code_interpreter"]
    tool_names = ["web_search", "code_interpreter", "data_analysis"]

    results = validator.validate_multiple_tools(tool_names, allowlist)

    assert results["web_search"] is True
    assert results["code_interpreter"] is True
    assert results["data_analysis"] is False


def test_validate_multiple_tools_empty_allowlist():
    """Test validating multiple tools with empty allowlist."""
    validator = ToolValidator()

    tool_names = ["web_search", "code_interpreter", "data_analysis"]

    results = validator.validate_multiple_tools(tool_names, [])

    # All should be allowed
    assert all(results.values())


def test_filter_allowed_tools():
    """Test filtering tools to only allowed ones."""
    validator = ToolValidator()

    allowlist = ["web_search", "code_interpreter"]
    tool_names = ["web_search", "code_interpreter", "data_analysis", "siem_query"]

    allowed = validator.filter_allowed_tools(tool_names, allowlist)

    assert len(allowed) == 2
    assert "web_search" in allowed
    assert "code_interpreter" in allowed
    assert "data_analysis" not in allowed
    assert "siem_query" not in allowed


def test_filter_allowed_tools_empty_allowlist():
    """Test that empty allowlist returns all tools."""
    validator = ToolValidator()

    tool_names = ["web_search", "code_interpreter", "data_analysis"]

    allowed = validator.filter_allowed_tools(tool_names, [])

    assert len(allowed) == 3
    assert allowed == tool_names


def test_filter_allowed_tools_none_allowed():
    """Test filtering when no tools are allowed."""
    validator = ToolValidator()

    allowlist = ["web_search"]
    tool_names = ["code_interpreter", "data_analysis", "siem_query"]

    allowed = validator.filter_allowed_tools(tool_names, allowlist)

    assert len(allowed) == 0


def test_get_validation_error_message_with_allowlist():
    """Test error message generation with allowlist."""
    validator = ToolValidator()

    allowlist = ["web_search", "code_interpreter"]

    message = validator.get_validation_error_message("data_analysis", allowlist)

    assert "data_analysis" in message
    assert "not permitted" in message
    assert "web_search" in message
    assert "code_interpreter" in message


def test_get_validation_error_message_empty_allowlist():
    """Test error message generation with empty allowlist."""
    validator = ToolValidator()

    message = validator.get_validation_error_message("any_tool", [])

    assert "any_tool" in message
    assert "not available" in message


def test_tool_call_validation_error():
    """Test ToolCallValidationError exception."""
    allowlist = ["web_search"]

    with pytest.raises(ToolCallValidationError) as exc_info:
        raise ToolCallValidationError("code_interpreter", allowlist)

    error = exc_info.value
    assert error.tool_name == "code_interpreter"
    assert error.allowlist == allowlist
    assert "code_interpreter" in str(error)
    assert "not permitted" in str(error)


def test_tool_call_validation_error_custom_message():
    """Test ToolCallValidationError with custom message."""
    allowlist = ["web_search"]
    custom_message = "Custom error message"

    with pytest.raises(ToolCallValidationError) as exc_info:
        raise ToolCallValidationError("code_interpreter", allowlist, custom_message)

    error = exc_info.value
    assert str(error) == custom_message


def test_tool_call_validation_error_empty_allowlist():
    """Test ToolCallValidationError with empty allowlist."""
    with pytest.raises(ToolCallValidationError) as exc_info:
        raise ToolCallValidationError("any_tool", [])

    error = exc_info.value
    assert "not available" in str(error)


def test_validator_with_registered_tools():
    """Test validator with tools registered in the registry."""
    registry = ToolRegistry()
    validator = ToolValidator(registry=registry)

    def mock_handler():
        return "test"

    # Register some tools
    metadata = ToolMetadata(
        name="web_search",
        description="A search tool",
        category=ToolCategory.WEB_SEARCH,
        version="1.0.0",
    )
    registry.register_tool("web_search", mock_handler, metadata)

    # Validator should still validate based on allowlist, not registry
    allowlist = ["web_search", "code_interpreter"]

    assert validator.validate_tool_call("web_search", allowlist) is True
    assert validator.validate_tool_call("code_interpreter", allowlist) is True


def test_validate_tool_empty_name():
    """Test validation with empty tool name."""
    validator = ToolValidator()

    allowlist = ["web_search"]

    # Empty string is not in allowlist
    assert validator.validate_tool_call("", allowlist) is False


def test_filter_preserves_order():
    """Test that filtering preserves tool order."""
    validator = ToolValidator()

    allowlist = ["tool_1", "tool_3"]
    tool_names = ["tool_1", "tool_2", "tool_3", "tool_4"]

    allowed = validator.filter_allowed_tools(tool_names, allowlist)

    assert allowed == ["tool_1", "tool_3"]


def test_validate_multiple_tools_empty_list():
    """Test validating empty list of tools."""
    validator = ToolValidator()

    results = validator.validate_multiple_tools([], ["web_search"])

    assert results == {}


# =============================================================================
# ADR-057: Security-based Tool Restrictions Tests
# =============================================================================


from src.orchestrator.app.schemas.tool import (
    DataFlowDirection,
    DataSourceType,
    MaxDataSensitivity,
    NetworkAccessLevel,
    ToolListItem,
    UseCaseToolRestrictions,
)
from src.orchestrator.app.schemas.tool import (
    ToolCategory as SchemaToolCategory,
)


def create_test_tool(
    tool_id: str = "test-tool",
    data_source_type: DataSourceType = DataSourceType.INTERNAL,
    data_flow_direction: DataFlowDirection = DataFlowDirection.INGRESS,
    network_access_level: NetworkAccessLevel = NetworkAccessLevel.INTERNAL,
    max_data_sensitivity: MaxDataSensitivity = MaxDataSensitivity.INTERNAL,
) -> ToolListItem:
    """Helper to create test tools with security classification."""
    import uuid

    return ToolListItem(
        id=uuid.uuid4(),
        tool_id=tool_id,
        name=f"Test Tool {tool_id}",
        description=f"Test tool {tool_id}",
        category=SchemaToolCategory.CUSTOM,
        is_enabled=True,
        is_healthy=True,
        requires_authentication=False,
        data_source_type=data_source_type,
        data_flow_direction=data_flow_direction,
        network_access_level=network_access_level,
        max_data_sensitivity=max_data_sensitivity,
    )


def test_validate_tool_security_no_restrictions():
    """Test that tool passes when no restrictions are set."""
    validator = ToolValidator()
    tool = create_test_tool()

    is_allowed, reason = validator.validate_tool_security(tool, None)

    assert is_allowed is True
    assert reason is None


def test_validate_tool_security_default_restrictions():
    """Test tool validation against default restrictions."""
    validator = ToolValidator()
    restrictions = UseCaseToolRestrictions()  # Default: internal + none, ingress + none

    # Internal tool should pass
    internal_tool = create_test_tool(
        tool_id="internal-tool",
        data_source_type=DataSourceType.INTERNAL,
        data_flow_direction=DataFlowDirection.INGRESS,
    )
    is_allowed, reason = validator.validate_tool_security(internal_tool, restrictions)
    assert is_allowed is True

    # External tool should fail
    external_tool = create_test_tool(
        tool_id="external-tool",
        data_source_type=DataSourceType.EXTERNAL,
    )
    is_allowed, reason = validator.validate_tool_security(external_tool, restrictions)
    assert is_allowed is False
    assert "data source" in reason.lower()


def test_validate_tool_security_egress_blocked():
    """Test that egress tools are blocked by default restrictions."""
    validator = ToolValidator()
    restrictions = UseCaseToolRestrictions()

    egress_tool = create_test_tool(
        tool_id="egress-tool",
        data_flow_direction=DataFlowDirection.EGRESS,
    )

    is_allowed, reason = validator.validate_tool_security(egress_tool, restrictions)

    assert is_allowed is False
    assert "data flow" in reason.lower()


def test_validate_tool_security_network_external_blocked():
    """Test that external network access is blocked by default restrictions."""
    validator = ToolValidator()
    restrictions = UseCaseToolRestrictions()

    external_network_tool = create_test_tool(
        tool_id="external-network-tool",
        network_access_level=NetworkAccessLevel.EXTERNAL,
    )

    is_allowed, reason = validator.validate_tool_security(external_network_tool, restrictions)

    assert is_allowed is False
    assert "network access" in reason.lower()


def test_validate_tool_security_sensitivity_insufficient():
    """Test that tools with insufficient sensitivity are rejected."""
    validator = ToolValidator()
    restrictions = UseCaseToolRestrictions(
        required_data_sensitivity=MaxDataSensitivity.CONFIDENTIAL
    )

    # Tool with only public sensitivity should fail
    public_tool = create_test_tool(
        tool_id="public-tool",
        max_data_sensitivity=MaxDataSensitivity.PUBLIC,
    )

    is_allowed, reason = validator.validate_tool_security(public_tool, restrictions)

    assert is_allowed is False
    assert "sensitivity" in reason.lower()


def test_validate_tool_security_explicit_blocklist():
    """Test that tools on explicit blocklist are always rejected."""
    validator = ToolValidator()
    restrictions = UseCaseToolRestrictions(
        explicit_tool_blocklist=["blocked-tool"],
    )

    # Tool on blocklist should fail even if it matches all criteria
    blocked_tool = create_test_tool(tool_id="blocked-tool")

    is_allowed, reason = validator.validate_tool_security(blocked_tool, restrictions)

    assert is_allowed is False
    assert "explicitly blocked" in reason.lower()


def test_validate_tool_security_explicit_allowlist():
    """Test that tools on explicit allowlist bypass other checks."""
    validator = ToolValidator()
    restrictions = UseCaseToolRestrictions(
        allowed_data_sources=[DataSourceType.INTERNAL],  # Only internal
        explicit_tool_allowlist=["special-external-tool"],
    )

    # External tool should normally fail but passes due to explicit allowlist
    special_tool = create_test_tool(
        tool_id="special-external-tool",
        data_source_type=DataSourceType.EXTERNAL,
    )

    is_allowed, _reason = validator.validate_tool_security(special_tool, restrictions)

    assert is_allowed is True


def test_validate_tool_full_both_checks():
    """Test full validation against both allowlist and security restrictions."""
    validator = ToolValidator()
    restrictions = UseCaseToolRestrictions()
    allowlist = ["approved-tool"]

    # Tool in allowlist but fails security
    external_approved = create_test_tool(
        tool_id="approved-tool",
        data_source_type=DataSourceType.EXTERNAL,  # Fails security
    )

    is_allowed, reason = validator.validate_tool_full(external_approved, allowlist, restrictions)

    assert is_allowed is False
    assert "data source" in reason.lower()


def test_validate_tool_full_not_in_allowlist():
    """Test that tool not in allowlist is rejected before security check."""
    validator = ToolValidator()
    restrictions = UseCaseToolRestrictions()
    allowlist = ["approved-tool"]

    unapproved = create_test_tool(tool_id="unapproved-tool")

    is_allowed, reason = validator.validate_tool_full(unapproved, allowlist, restrictions)

    assert is_allowed is False
    assert "not permitted" in reason.lower()


def test_filter_tools_by_restrictions():
    """Test filtering multiple tools by security restrictions."""
    validator = ToolValidator()
    restrictions = UseCaseToolRestrictions(
        allowed_data_sources=[DataSourceType.INTERNAL, DataSourceType.NONE],
    )

    tools = [
        create_test_tool("internal-1", data_source_type=DataSourceType.INTERNAL),
        create_test_tool("external-1", data_source_type=DataSourceType.EXTERNAL),
        create_test_tool("internal-2", data_source_type=DataSourceType.INTERNAL),
        create_test_tool("none-1", data_source_type=DataSourceType.NONE),
    ]

    allowed, rejected = validator.filter_tools_by_restrictions(tools, restrictions)

    assert len(allowed) == 3
    assert len(rejected) == 1
    assert rejected[0][0] == "external-1"


def test_filter_tools_by_restrictions_none():
    """Test that no filtering occurs when restrictions are None."""
    validator = ToolValidator()

    tools = [
        create_test_tool("tool-1"),
        create_test_tool("tool-2"),
    ]

    allowed, rejected = validator.filter_tools_by_restrictions(tools, None)

    assert len(allowed) == 2
    assert len(rejected) == 0


def test_restriction_presets():
    """Test that RESTRICTION_PRESETS are correctly defined."""
    from src.orchestrator.app.schemas.tool import RESTRICTION_PRESETS

    # Test high_security preset
    high_sec = RESTRICTION_PRESETS["high_security"]
    assert DataSourceType.EXTERNAL not in high_sec.allowed_data_sources
    assert DataFlowDirection.EGRESS not in high_sec.allowed_data_flows
    assert NetworkAccessLevel.EXTERNAL not in high_sec.allowed_network_levels
    assert high_sec.required_data_sensitivity == MaxDataSensitivity.RESTRICTED

    # Test research_open preset
    research = RESTRICTION_PRESETS["research_open"]
    assert DataSourceType.EXTERNAL in research.allowed_data_sources
    assert NetworkAccessLevel.EXTERNAL in research.allowed_network_levels
    assert research.required_data_sensitivity == MaxDataSensitivity.PUBLIC
