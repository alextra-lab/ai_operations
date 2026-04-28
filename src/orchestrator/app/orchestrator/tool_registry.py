"""
Tool Registry for AI Operations Platform.

This module provides a framework for managing and registering tools
that can be used during orchestration. This is a placeholder for future
MCP (Model Context Protocol) integration and tool calling capabilities.

The registry maintains a catalog of available tools and their handlers,
enabling dynamic tool discovery and execution.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from shared.logging_utils.fastapi import get_logger

logger = get_logger(__name__)


class ToolCategory(str, Enum):
    """Categories for tool classification."""

    WEB_SEARCH = "web_search"
    CODE_INTERPRETER = "code_interpreter"
    DATA_ANALYSIS = "data_analysis"
    THREAT_INTEL = "threat_intel"
    SIEM_QUERY = "siem_query"
    CUSTOM = "custom"


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""

    name: str
    description: str
    category: ToolCategory
    version: str
    parameters_schema: dict[str, Any] | None = None
    requires_auth: bool = False
    rate_limit: int | None = None


class ToolRegistry:
    """
    Registry for managing available tools.

    This is a placeholder implementation for future MCP integration.
    Tools can be registered with handlers and metadata for dynamic execution.

    Example:
        >>> registry = ToolRegistry()
        >>> registry.register_tool(
        ...     name="web_search",
        ...     handler=search_handler,
        ...     metadata=ToolMetadata(...)
        ... )
    """

    def __init__(self) -> None:
        """Initialize the tool registry."""
        self._tools: dict[str, Callable] = {}
        self._metadata: dict[str, ToolMetadata] = {}
        logger.info("Tool registry initialized")

    def register_tool(self, name: str, handler: Callable, metadata: ToolMetadata) -> None:
        """
        Register a tool with its handler and metadata.

        Args:
            name: Unique identifier for the tool
            handler: Callable function to execute the tool
            metadata: Metadata describing the tool

        Raises:
            ValueError: If tool name is already registered
        """
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered")

        self._tools[name] = handler
        self._metadata[name] = metadata
        logger.info(
            "Registered tool: %s (category=%s, version=%s)",
            name,
            metadata.category,
            metadata.version,
        )

    def unregister_tool(self, name: str) -> None:
        """
        Unregister a tool from the registry.

        Args:
            name: Name of the tool to unregister

        Raises:
            KeyError: If tool name is not registered
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered")

        del self._tools[name]
        del self._metadata[name]
        logger.info("Unregistered tool: %s", name)

    def get_tool(self, name: str) -> Callable | None:
        """
        Get the handler for a registered tool.

        Args:
            name: Name of the tool

        Returns:
            Tool handler callable, or None if not found
        """
        return self._tools.get(name)

    def get_metadata(self, name: str) -> ToolMetadata | None:
        """
        Get metadata for a registered tool.

        Args:
            name: Name of the tool

        Returns:
            Tool metadata, or None if not found
        """
        return self._metadata.get(name)

    def is_registered(self, name: str) -> bool:
        """
        Check if a tool is registered.

        Args:
            name: Name of the tool

        Returns:
            True if tool is registered, False otherwise
        """
        return name in self._tools

    def list_tools(self, category: ToolCategory | None = None) -> list[str]:
        """
        List all registered tools, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of tool names
        """
        if category is None:
            return list(self._tools.keys())

        return [name for name, metadata in self._metadata.items() if metadata.category == category]

    def get_all_metadata(self) -> dict[str, ToolMetadata]:
        """
        Get metadata for all registered tools.

        Returns:
            Dictionary mapping tool names to metadata
        """
        return dict(self._metadata)


# Global registry instance
_global_registry: ToolRegistry | None = None


def get_global_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.

    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_global_registry() -> None:
    """
    Reset the global tool registry instance.

    Useful for testing purposes.
    """
    global _global_registry
    _global_registry = None
