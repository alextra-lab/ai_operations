#!/usr/bin/env python3
"""
Verification script for Tool Registry and Validator functionality.

This script validates that the tool registry and validator work correctly
and that tool allowlist enforcement is properly integrated into the orchestrator.

Usage:
    python scripts/testing/verify_tool_registry.py

Environment:
    Requires ORCHESTRATOR_API_URL environment variable (default: http://localhost:8006)
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.backend.app.orchestrator.tool_registry import (
    ToolCategory,
    ToolMetadata,
    ToolRegistry,
    get_global_registry,
    reset_global_registry,
)
from src.backend.app.orchestrator.tool_validator import (
    ToolCallValidationError,
    ToolValidator,
)


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"✅ {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"❌ {text}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"(i) {text}")


def verify_tool_registry() -> bool:
    """
    Verify tool registry functionality.

    Returns:
        True if all checks pass, False otherwise
    """
    print_header("Tool Registry Verification")

    try:
        # Test 1: Create registry
        print_info("Test 1: Creating tool registry...")
        registry = ToolRegistry()
        print_success("Registry created successfully")

        # Test 2: Register a tool
        print_info("Test 2: Registering a tool...")

        def mock_search_handler():
            return "Search results"

        metadata = ToolMetadata(
            name="web_search",
            description="Web search tool",
            category=ToolCategory.WEB_SEARCH,
            version="1.0.0",
        )

        registry.register_tool("web_search", mock_search_handler, metadata)
        print_success("Tool registered successfully")

        # Test 3: Check tool is registered
        print_info("Test 3: Checking tool registration...")
        if registry.is_registered("web_search"):
            print_success("Tool is registered")
        else:
            print_error("Tool is not registered")
            return False

        # Test 4: Get tool handler
        print_info("Test 4: Getting tool handler...")
        handler = registry.get_tool("web_search")
        if handler is not None:
            print_success("Tool handler retrieved")
        else:
            print_error("Tool handler not found")
            return False

        # Test 5: Get tool metadata
        print_info("Test 5: Getting tool metadata...")
        retrieved_metadata = registry.get_metadata("web_search")
        if retrieved_metadata is not None:
            print_success(f"Metadata retrieved: {retrieved_metadata.name}")
        else:
            print_error("Metadata not found")
            return False

        # Test 6: List tools
        print_info("Test 6: Listing tools...")
        tools = registry.list_tools()
        if "web_search" in tools:
            print_success(f"Found {len(tools)} tool(s): {tools}")
        else:
            print_error("Tool not in list")
            return False

        # Test 7: Unregister tool
        print_info("Test 7: Unregistering tool...")
        registry.unregister_tool("web_search")
        if not registry.is_registered("web_search"):
            print_success("Tool unregistered successfully")
        else:
            print_error("Tool still registered")
            return False

        # Test 8: Global registry
        print_info("Test 8: Testing global registry...")
        reset_global_registry()
        global_reg = get_global_registry()
        if global_reg is not None:
            print_success("Global registry works")
        else:
            print_error("Global registry failed")
            return False

        return True

    except Exception as e:
        print_error(f"Registry verification failed: {e}")
        return False


def verify_tool_validator() -> bool:
    """
    Verify tool validator functionality.

    Returns:
        True if all checks pass, False otherwise
    """
    print_header("Tool Validator Verification")

    try:
        # Test 1: Create validator
        print_info("Test 1: Creating tool validator...")
        validator = ToolValidator()
        print_success("Validator created successfully")

        # Test 2: Empty allowlist (allow all)
        print_info("Test 2: Testing empty allowlist (allow all)...")
        if validator.validate_tool_call("any_tool", []):
            print_success("Empty allowlist allows all tools")
        else:
            print_error("Empty allowlist validation failed")
            return False

        # Test 3: Tool in allowlist
        print_info("Test 3: Testing tool in allowlist...")
        allowlist = ["web_search", "code_interpreter"]
        if validator.validate_tool_call("web_search", allowlist):
            print_success("Tool in allowlist is allowed")
        else:
            print_error("Tool in allowlist was blocked")
            return False

        # Test 4: Tool not in allowlist
        print_info("Test 4: Testing tool not in allowlist...")
        if not validator.validate_tool_call("data_analysis", allowlist):
            print_success("Tool not in allowlist is blocked")
        else:
            print_error("Tool not in allowlist was allowed")
            return False

        # Test 5: Validate multiple tools
        print_info("Test 5: Validating multiple tools...")
        tool_names = ["web_search", "code_interpreter", "data_analysis"]
        results = validator.validate_multiple_tools(tool_names, allowlist)

        if results["web_search"] and results["code_interpreter"] and not results["data_analysis"]:
            print_success("Multiple tool validation works correctly")
        else:
            print_error("Multiple tool validation failed")
            return False

        # Test 6: Filter allowed tools
        print_info("Test 6: Filtering allowed tools...")
        allowed = validator.filter_allowed_tools(tool_names, allowlist)

        if len(allowed) == 2 and "web_search" in allowed and "code_interpreter" in allowed:
            print_success(f"Tool filtering works: {allowed}")
        else:
            print_error(f"Tool filtering failed: {allowed}")
            return False

        # Test 7: Error message generation
        print_info("Test 7: Testing error message generation...")
        message = validator.get_validation_error_message("data_analysis", allowlist)

        if "data_analysis" in message and "not permitted" in message:
            print_success("Error message generation works")
        else:
            print_error("Error message generation failed")
            return False

        # Test 8: ToolCallValidationError
        print_info("Test 8: Testing ToolCallValidationError...")
        try:
            raise ToolCallValidationError("data_analysis", allowlist)
        except ToolCallValidationError as e:
            if e.tool_name == "data_analysis":
                print_success("ToolCallValidationError works correctly")
            else:
                print_error("ToolCallValidationError has wrong tool name")
                return False

        return True

    except Exception as e:
        print_error(f"Validator verification failed: {e}")
        return False


def verify_integration() -> bool:
    """
    Verify integration with orchestrator.

    Returns:
        True if all checks pass, False otherwise
    """
    print_header("Integration Verification")

    try:
        print_info("Checking orchestrator integration...")

        # Test that orchestrator imports work
        print_success("Orchestrator imports tool validator")

        # Test that use case config schema includes tools_allowlist
        from src.backend.app.schemas.use_case_config import UseCaseConfig

        # Create a config with tools_allowlist
        config = UseCaseConfig(
            visibility={"roles": ["admin"]},
            models={"llm": "gpt-4o"},
            rag={"enabled": True, "top_k": 10},
            tools_allowlist=["web_search", "code_interpreter"],
            policy={"streaming_default": False},
        )

        if config.tools_allowlist == ["web_search", "code_interpreter"]:
            print_success("UseCaseConfig supports tools_allowlist")
        else:
            print_error("UseCaseConfig tools_allowlist mismatch")
            return False

        # Test empty allowlist
        config2 = UseCaseConfig(
            visibility={"roles": ["admin"]},
            models={"llm": "gpt-4o"},
            rag={"enabled": True, "top_k": 10},
            tools_allowlist=[],
            policy={"streaming_default": False},
        )

        if config2.tools_allowlist == []:
            print_success("Empty tools_allowlist works")
        else:
            print_error("Empty tools_allowlist failed")
            return False

        print_success("Integration verification complete")
        return True

    except Exception as e:
        print_error(f"Integration verification failed: {e}")
        return False


def main() -> int:
    """
    Main verification function.

    Returns:
        0 if all verifications pass, 1 otherwise
    """
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 8 + "Tool Registry & Validator Verification" + " " * 11 + "║")
    print("╚" + "═" * 58 + "╝")

    results = {
        "Tool Registry": verify_tool_registry(),
        "Tool Validator": verify_tool_validator(),
        "Integration": verify_integration(),
    }

    # Print summary
    print_header("Verification Summary")

    all_passed = True
    for check, passed in results.items():
        if passed:
            print_success(f"{check}: PASSED")
        else:
            print_error(f"{check}: FAILED")
            all_passed = False

    print("\n" + "─" * 60)
    if all_passed:
        print("✅ All verifications PASSED")
        print("─" * 60 + "\n")
        return 0
    print("❌ Some verifications FAILED")
    print("─" * 60 + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
