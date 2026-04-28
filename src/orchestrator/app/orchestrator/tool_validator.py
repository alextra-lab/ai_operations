"""
Tool Validator for AI Operations Platform.

This module provides validation logic for tool calls against configured
allowlists and security-based restrictions (ADR-057). It enforces that
only permitted tools can be executed within a given use case context.

This is part of the security framework for MCP integration and ensures
that use cases can restrict which tools are available based on both:
1. Simple allowlists (tools_allowlist)
2. Security classification (tool_restrictions per ADR-057)
"""

from shared.logging_utils.fastapi import get_logger

from ..schemas.tool import ToolListItem, UseCaseToolRestrictions
from .tool_registry import ToolRegistry, get_global_registry

logger = get_logger(__name__)


class ToolValidator:
    """
    Validator for tool calls against allowlists.

    This class provides validation logic to ensure that tool calls
    respect the configured allowlists for a given use case.

    Empty allowlists (default) allow all tools. Non-empty allowlists
    restrict to only the specified tools.

    Example:
        >>> validator = ToolValidator()
        >>> validator.validate_tool_call("web_search", ["web_search", "data_analysis"])
        True
        >>> validator.validate_tool_call("code_interpreter", ["web_search"])
        False
    """

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        """
        Initialize the tool validator.

        Args:
            registry: Tool registry to validate against (uses global if None)
        """
        self.registry = registry or get_global_registry()
        logger.debug("Tool validator initialized")

    def validate_tool_call(self, tool_name: str, allowlist: list[str]) -> bool:
        """
        Validate if a tool call is permitted by the allowlist.

        Args:
            tool_name: Name of the tool being called
            allowlist: List of allowed tool names (empty = allow all)

        Returns:
            True if tool is allowed, False otherwise

        Notes:
            - Empty allowlist allows all tools
            - Non-empty allowlist restricts to specified tools
            - Tool name matching is case-sensitive
        """
        # Empty allowlist = allow all tools
        if not allowlist:
            logger.debug("Tool '%s' allowed (empty allowlist)", tool_name)
            return True

        # Check if tool is in allowlist
        is_allowed = tool_name in allowlist

        if is_allowed:
            logger.debug("Tool '%s' allowed by allowlist", tool_name)
        else:
            logger.warning(
                "Tool '%s' blocked by allowlist. Allowed tools: %s",
                tool_name,
                allowlist,
            )

        return is_allowed

    def validate_multiple_tools(
        self, tool_names: list[str], allowlist: list[str]
    ) -> dict[str, bool]:
        """
        Validate multiple tool calls at once.

        Args:
            tool_names: List of tool names to validate
            allowlist: List of allowed tool names

        Returns:
            Dictionary mapping tool names to validation results
        """
        results = {}
        for tool_name in tool_names:
            results[tool_name] = self.validate_tool_call(tool_name, allowlist)
        return results

    def filter_allowed_tools(self, tool_names: list[str], allowlist: list[str]) -> list[str]:
        """
        Filter a list of tool names to only those allowed.

        Args:
            tool_names: List of tool names to filter
            allowlist: List of allowed tool names

        Returns:
            List of tool names that are allowed
        """
        if not allowlist:
            return tool_names

        allowed = [name for name in tool_names if name in allowlist]

        blocked_count = len(tool_names) - len(allowed)
        if blocked_count > 0:
            logger.info("Filtered %d tools by allowlist. Allowed: %s", blocked_count, allowed)

        return allowed

    def get_validation_error_message(self, tool_name: str, allowlist: list[str]) -> str:
        """
        Get a user-friendly error message for a blocked tool.

        Args:
            tool_name: Name of the blocked tool
            allowlist: List of allowed tool names

        Returns:
            Error message string
        """
        if not allowlist:
            return f"Tool '{tool_name}' is not available"

        return (
            f"Tool '{tool_name}' is not permitted for this use case. "
            f"Allowed tools: {', '.join(allowlist)}"
        )

    # =========================================================================
    # ADR-057: Security-based tool restrictions
    # =========================================================================

    def validate_tool_security(
        self,
        tool: ToolListItem,
        restrictions: UseCaseToolRestrictions | None,
    ) -> tuple[bool, str | None]:
        """
        Validate if a tool meets security restrictions.

        Args:
            tool: Tool information including security classification
            restrictions: Security restrictions for the use case (None = no restrictions)

        Returns:
            Tuple of (is_allowed, rejection_reason)
        """
        if restrictions is None:
            logger.debug("Tool '%s' allowed (no security restrictions)", tool.tool_id)
            return True, None

        is_allowed, reason = restrictions.is_tool_allowed(tool)

        if is_allowed:
            logger.debug("Tool '%s' passed security validation", tool.tool_id)
        else:
            logger.warning(
                "Tool '%s' blocked by security restrictions: %s",
                tool.tool_id,
                reason,
            )

        return is_allowed, reason

    def validate_tool_full(
        self,
        tool: ToolListItem,
        allowlist: list[str],
        restrictions: UseCaseToolRestrictions | None,
    ) -> tuple[bool, str | None]:
        """
        Validate a tool against both allowlist and security restrictions.

        This is the primary validation method that checks both:
        1. Simple allowlist (tools_allowlist)
        2. Security restrictions (tool_restrictions per ADR-057)

        Args:
            tool: Tool information including security classification
            allowlist: List of allowed tool names (empty = allow all)
            restrictions: Security restrictions (None = no restrictions)

        Returns:
            Tuple of (is_allowed, rejection_reason)
        """
        # Check allowlist first
        if not self.validate_tool_call(tool.tool_id, allowlist):
            return False, self.get_validation_error_message(tool.tool_id, allowlist)

        # Check security restrictions
        return self.validate_tool_security(tool, restrictions)

    def filter_tools_by_restrictions(
        self,
        tools: list[ToolListItem],
        restrictions: UseCaseToolRestrictions | None,
    ) -> tuple[list[ToolListItem], list[tuple[str, str]]]:
        """
        Filter tools by security restrictions.

        Args:
            tools: List of tools to filter
            restrictions: Security restrictions (None = no filtering)

        Returns:
            Tuple of (allowed_tools, rejected_tools_with_reasons)
        """
        if restrictions is None:
            return tools, []

        allowed = []
        rejected = []

        for tool in tools:
            is_allowed, reason = restrictions.is_tool_allowed(tool)
            if is_allowed:
                allowed.append(tool)
            else:
                rejected.append((tool.tool_id, reason or "Unknown reason"))

        if rejected:
            logger.info(
                "Security restrictions filtered %d tools. Rejected: %s",
                len(rejected),
                [r[0] for r in rejected],
            )

        return allowed, rejected


class ToolCallValidationError(Exception):
    """Exception raised when a tool call fails validation."""

    def __init__(self, tool_name: str, allowlist: list[str], message: str | None = None):
        """
        Initialize the validation error.

        Args:
            tool_name: Name of the tool that failed validation
            allowlist: The allowlist that blocked the tool
            message: Optional custom error message
        """
        self.tool_name = tool_name
        self.allowlist = allowlist

        if message is None:
            validator = ToolValidator()
            message = validator.get_validation_error_message(tool_name, allowlist)

        super().__init__(message)
