"""
Unit tests for Tool Registry.

Tests the tool registration, unregistration, and discovery functionality.
"""

import pytest

from src.orchestrator.app.orchestrator.tool_registry import (
    ToolCategory,
    ToolMetadata,
    ToolRegistry,
    get_global_registry,
    reset_global_registry,
)


def test_registry_initialization():
    """Test that registry initializes correctly."""
    registry = ToolRegistry()
    assert registry._tools == {}
    assert registry._metadata == {}


def test_register_tool():
    """Test tool registration."""
    registry = ToolRegistry()

    def mock_handler():
        return "test"

    metadata = ToolMetadata(
        name="test_tool",
        description="A test tool",
        category=ToolCategory.WEB_SEARCH,
        version="1.0.0",
    )

    registry.register_tool("test_tool", mock_handler, metadata)

    assert registry.is_registered("test_tool")
    assert registry.get_tool("test_tool") == mock_handler
    assert registry.get_metadata("test_tool") == metadata


def test_register_duplicate_tool_raises_error():
    """Test that registering a duplicate tool raises ValueError."""
    registry = ToolRegistry()

    def mock_handler():
        return "test"

    metadata = ToolMetadata(
        name="test_tool",
        description="A test tool",
        category=ToolCategory.WEB_SEARCH,
        version="1.0.0",
    )

    registry.register_tool("test_tool", mock_handler, metadata)

    with pytest.raises(ValueError, match="already registered"):
        registry.register_tool("test_tool", mock_handler, metadata)


def test_unregister_tool():
    """Test tool unregistration."""
    registry = ToolRegistry()

    def mock_handler():
        return "test"

    metadata = ToolMetadata(
        name="test_tool",
        description="A test tool",
        category=ToolCategory.WEB_SEARCH,
        version="1.0.0",
    )

    registry.register_tool("test_tool", mock_handler, metadata)
    assert registry.is_registered("test_tool")

    registry.unregister_tool("test_tool")
    assert not registry.is_registered("test_tool")


def test_unregister_nonexistent_tool_raises_error():
    """Test that unregistering a nonexistent tool raises KeyError."""
    registry = ToolRegistry()

    with pytest.raises(KeyError, match="not registered"):
        registry.unregister_tool("nonexistent_tool")


def test_get_nonexistent_tool():
    """Test getting a nonexistent tool returns None."""
    registry = ToolRegistry()

    assert registry.get_tool("nonexistent") is None
    assert registry.get_metadata("nonexistent") is None


def test_is_registered():
    """Test checking if tool is registered."""
    registry = ToolRegistry()

    assert not registry.is_registered("test_tool")

    def mock_handler():
        return "test"

    metadata = ToolMetadata(
        name="test_tool",
        description="A test tool",
        category=ToolCategory.WEB_SEARCH,
        version="1.0.0",
    )

    registry.register_tool("test_tool", mock_handler, metadata)
    assert registry.is_registered("test_tool")


def test_list_all_tools():
    """Test listing all tools."""
    registry = ToolRegistry()

    def mock_handler():
        return "test"

    for i, category in enumerate([ToolCategory.WEB_SEARCH, ToolCategory.CODE_INTERPRETER]):
        metadata = ToolMetadata(
            name=f"tool_{i}",
            description=f"Tool {i}",
            category=category,
            version="1.0.0",
        )
        registry.register_tool(f"tool_{i}", mock_handler, metadata)

    tools = registry.list_tools()
    assert len(tools) == 2
    assert "tool_0" in tools
    assert "tool_1" in tools


def test_list_tools_by_category():
    """Test listing tools filtered by category."""
    registry = ToolRegistry()

    def mock_handler():
        return "test"

    # Register tools in different categories
    metadata1 = ToolMetadata(
        name="search_tool",
        description="A search tool",
        category=ToolCategory.WEB_SEARCH,
        version="1.0.0",
    )
    registry.register_tool("search_tool", mock_handler, metadata1)

    metadata2 = ToolMetadata(
        name="code_tool",
        description="A code tool",
        category=ToolCategory.CODE_INTERPRETER,
        version="1.0.0",
    )
    registry.register_tool("code_tool", mock_handler, metadata2)

    # Filter by category
    search_tools = registry.list_tools(category=ToolCategory.WEB_SEARCH)
    assert len(search_tools) == 1
    assert "search_tool" in search_tools

    code_tools = registry.list_tools(category=ToolCategory.CODE_INTERPRETER)
    assert len(code_tools) == 1
    assert "code_tool" in code_tools


def test_get_all_metadata():
    """Test getting all tool metadata."""
    registry = ToolRegistry()

    def mock_handler():
        return "test"

    metadata1 = ToolMetadata(
        name="tool_1",
        description="Tool 1",
        category=ToolCategory.WEB_SEARCH,
        version="1.0.0",
    )
    registry.register_tool("tool_1", mock_handler, metadata1)

    metadata2 = ToolMetadata(
        name="tool_2",
        description="Tool 2",
        category=ToolCategory.CODE_INTERPRETER,
        version="1.0.0",
    )
    registry.register_tool("tool_2", mock_handler, metadata2)

    all_metadata = registry.get_all_metadata()
    assert len(all_metadata) == 2
    assert all_metadata["tool_1"] == metadata1
    assert all_metadata["tool_2"] == metadata2


def test_global_registry():
    """Test global registry singleton."""
    # Reset to ensure clean state
    reset_global_registry()

    registry1 = get_global_registry()
    registry2 = get_global_registry()

    # Should be the same instance
    assert registry1 is registry2


def test_reset_global_registry():
    """Test resetting the global registry."""
    # Get initial registry
    registry1 = get_global_registry()

    # Register a tool
    def mock_handler():
        return "test"

    metadata = ToolMetadata(
        name="test_tool",
        description="A test tool",
        category=ToolCategory.WEB_SEARCH,
        version="1.0.0",
    )
    registry1.register_tool("test_tool", mock_handler, metadata)

    # Reset
    reset_global_registry()

    # Get new registry
    registry2 = get_global_registry()

    # Should be a different instance
    assert registry1 is not registry2

    # New registry should be empty
    assert not registry2.is_registered("test_tool")


def test_tool_metadata_with_optional_fields():
    """Test tool metadata with optional fields."""
    metadata = ToolMetadata(
        name="advanced_tool",
        description="An advanced tool",
        category=ToolCategory.THREAT_INTEL,
        version="2.0.0",
        parameters_schema={"type": "object", "properties": {}},
        requires_auth=True,
        rate_limit=100,
    )

    assert metadata.parameters_schema is not None
    assert metadata.requires_auth is True
    assert metadata.rate_limit == 100


def test_tool_metadata_defaults():
    """Test tool metadata default values."""
    metadata = ToolMetadata(
        name="simple_tool",
        description="A simple tool",
        category=ToolCategory.CUSTOM,
        version="1.0.0",
    )

    assert metadata.parameters_schema is None
    assert metadata.requires_auth is False
    assert metadata.rate_limit is None
