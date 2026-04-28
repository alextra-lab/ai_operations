"""
Tool result processing service.

Formats tool results for LLM consumption and response formatting.
"""

import json
from typing import Any

from shared.logging_utils.fastapi import configure_logging

logger = configure_logging(service_name="tool_result_processor")


class ToolResultProcessor:
    """Process and format tool execution results."""

    @staticmethod
    def format_for_llm(tool_results: list[dict[str, Any]]) -> str:
        """
        Format tool results for LLM context injection.

        Args:
            tool_results: List of tool execution results with keys:
                - tool: Tool name/ID
                - status: "success" or "error"
                - result: Result data (if success)
                - error: Error message (if error)
                - duration_ms: Execution duration (optional)

        Returns:
            Formatted string for LLM context
        """
        formatted_parts = []

        for result in tool_results:
            tool_name = result.get("tool", "unknown")
            status = result.get("status", "error")

            if status == "success":
                result_data = result.get("result")
                # Format result data nicely
                if isinstance(result_data, dict):
                    formatted_result = json.dumps(result_data, indent=2)
                elif isinstance(result_data, str):
                    formatted_result = result_data
                else:
                    formatted_result = json.dumps(result_data, indent=2)

                formatted_parts.append(f"Tool: {tool_name}\nResult: {formatted_result}\n")
            else:
                error = result.get("error", "Unknown error")
                formatted_parts.append(f"Tool: {tool_name}\nError: {error}\n")

        return "\n".join(formatted_parts)

    @staticmethod
    def format_for_response(tool_results: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Format tool results for API response metadata.

        Args:
            tool_results: List of tool execution results

        Returns:
            Formatted metadata dict with:
                - tools_invoked: List of tool names
                - tool_call_count: Total number of tool calls
                - tool_successes: Number of successful calls
                - tool_failures: Number of failed calls
                - tool_details: List of per-tool details
        """
        return {
            "tools_invoked": [r.get("tool", "unknown") for r in tool_results],
            "tool_call_count": len(tool_results),
            "tool_successes": sum(1 for r in tool_results if r.get("status") == "success"),
            "tool_failures": sum(1 for r in tool_results if r.get("status") == "error"),
            "tool_details": [
                {
                    "tool": r.get("tool", "unknown"),
                    "status": r.get("status", "error"),
                    "duration_ms": r.get("duration_ms"),
                }
                for r in tool_results
            ],
        }

    @staticmethod
    def extract_citations_from_tools(
        tool_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Extract citations from tool results (for sources).

        Args:
            tool_results: List of tool execution results

        Returns:
            List of source citations with:
                - source_type: "tool"
                - tool_name: Name of the tool
                - title: Source title (if available)
                - url: Source URL (if available)
                - snippet: Source snippet (if available)
        """
        citations = []

        for result in tool_results:
            if result.get("status") != "success":
                continue

            tool_name = result.get("tool", "unknown")
            result_data = result.get("result", {})

            # Extract URLs, documents, or other citable content
            if isinstance(result_data, dict):
                # Check for sources array
                if "sources" in result_data and isinstance(result_data["sources"], list):
                    for source in result_data["sources"]:
                        if isinstance(source, dict):
                            citations.append(
                                {
                                    "source_type": "tool",
                                    "tool_name": tool_name,
                                    "title": source.get("title"),
                                    "url": source.get("url"),
                                    "snippet": source.get("snippet"),
                                }
                            )
                # Check for direct URL field
                elif "url" in result_data:
                    citations.append(
                        {
                            "source_type": "tool",
                            "tool_name": tool_name,
                            "title": result_data.get("title"),
                            "url": result_data.get("url"),
                            "snippet": result_data.get("snippet"),
                        }
                    )
                # Check for document references
                elif "document_id" in result_data or "document_url" in result_data:
                    citations.append(
                        {
                            "source_type": "tool",
                            "tool_name": tool_name,
                            "title": result_data.get("title"),
                            "url": result_data.get("document_url"),
                            "snippet": result_data.get("snippet"),
                        }
                    )

        return citations

    @staticmethod
    def normalize_execution_result(
        tool_name: str,
        exec_result: dict[str, Any] | None,
        error: str | None = None,
        duration_ms: float | None = None,
    ) -> dict[str, Any]:
        """
        Normalize tool execution result into standard format.

        Args:
            tool_name: Name of the tool
            exec_result: Raw execution result from ToolExecutor
            error: Error message if execution failed
            duration_ms: Execution duration in milliseconds

        Returns:
            Normalized result dict with: tool, status, result/error, duration_ms
        """
        if error:
            return {
                "tool": tool_name,
                "status": "error",
                "error": error,
                "duration_ms": duration_ms,
            }

        # Normalize success result
        # ToolExecutor returns dict[str, Any] which could be {"result": <data>} or just <data>
        if exec_result is None:
            return {
                "tool": tool_name,
                "status": "success",
                "result": None,
                "duration_ms": duration_ms,
            }

        # If exec_result already has "result" key, use it
        if "result" in exec_result and len(exec_result) == 1:
            return {
                "tool": tool_name,
                "status": "success",
                "result": exec_result["result"],
                "duration_ms": duration_ms,
            }

        # Otherwise, use exec_result as-is
        return {
            "tool": tool_name,
            "status": "success",
            "result": exec_result,
            "duration_ms": duration_ms,
        }
