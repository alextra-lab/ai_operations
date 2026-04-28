"""
Unit tests for ToolResultProcessor service.

Tests result formatting for LLM context, API responses, and citation extraction.
"""

from app.services.tool_result_processor import ToolResultProcessor


class TestToolResultProcessor:
    """Tests for ToolResultProcessor class."""

    def test_format_for_llm_success(self):
        """Test formatting successful tool results for LLM."""
        tool_results = [
            {
                "tool": "web-scraper",
                "status": "success",
                "result": {"url": "https://example.com", "content": "Test content"},
                "duration_ms": 150.5,
            }
        ]

        formatted = ToolResultProcessor.format_for_llm(tool_results)

        assert "Tool: web-scraper" in formatted
        assert "Result:" in formatted
        assert "https://example.com" in formatted
        assert "Test content" in formatted

    def test_format_for_llm_error(self):
        """Test formatting error tool results for LLM."""
        tool_results = [
            {
                "tool": "web-scraper",
                "status": "error",
                "error": "Connection timeout",
                "duration_ms": 5000.0,
            }
        ]

        formatted = ToolResultProcessor.format_for_llm(tool_results)

        assert "Tool: web-scraper" in formatted
        assert "Error: Connection timeout" in formatted

    def test_format_for_llm_mixed_results(self):
        """Test formatting mixed success and error results."""
        tool_results = [
            {
                "tool": "web-scraper",
                "status": "success",
                "result": {"content": "Success"},
            },
            {
                "tool": "database-query",
                "status": "error",
                "error": "Query failed",
            },
        ]

        formatted = ToolResultProcessor.format_for_llm(tool_results)

        assert "Tool: web-scraper" in formatted
        assert "Result:" in formatted
        assert "Success" in formatted
        assert "Tool: database-query" in formatted
        assert "Error: Query failed" in formatted

    def test_format_for_llm_string_result(self):
        """Test formatting string result (non-dict)."""
        tool_results = [
            {
                "tool": "text-processor",
                "status": "success",
                "result": "Simple string result",
            }
        ]

        formatted = ToolResultProcessor.format_for_llm(tool_results)

        assert "Tool: text-processor" in formatted
        assert "Simple string result" in formatted

    def test_format_for_llm_none_result(self):
        """Test formatting None result."""
        tool_results = [{"tool": "void-tool", "status": "success", "result": None}]

        formatted = ToolResultProcessor.format_for_llm(tool_results)

        assert "Tool: void-tool" in formatted
        assert "null" in formatted or "None" in formatted

    def test_format_for_response_success(self):
        """Test formatting tool results for API response metadata."""
        tool_results = [
            {
                "tool": "web-scraper",
                "status": "success",
                "duration_ms": 150.5,
            },
            {
                "tool": "database-query",
                "status": "success",
                "duration_ms": 75.2,
            },
        ]

        metadata = ToolResultProcessor.format_for_response(tool_results)

        assert metadata["tool_call_count"] == 2
        assert metadata["tool_successes"] == 2
        assert metadata["tool_failures"] == 0
        assert len(metadata["tools_invoked"]) == 2
        assert "web-scraper" in metadata["tools_invoked"]
        assert "database-query" in metadata["tools_invoked"]
        assert len(metadata["tool_details"]) == 2
        assert metadata["tool_details"][0]["tool"] == "web-scraper"
        assert metadata["tool_details"][0]["status"] == "success"
        assert metadata["tool_details"][0]["duration_ms"] == 150.5

    def test_format_for_response_mixed(self):
        """Test formatting mixed success/error results for API."""
        tool_results = [
            {
                "tool": "web-scraper",
                "status": "success",
                "duration_ms": 150.5,
            },
            {
                "tool": "database-query",
                "status": "error",
                "duration_ms": 5000.0,
            },
        ]

        metadata = ToolResultProcessor.format_for_response(tool_results)

        assert metadata["tool_call_count"] == 2
        assert metadata["tool_successes"] == 1
        assert metadata["tool_failures"] == 1
        assert metadata["tool_details"][0]["status"] == "success"
        assert metadata["tool_details"][1]["status"] == "error"

    def test_format_for_response_empty(self):
        """Test formatting empty tool results."""
        tool_results = []

        metadata = ToolResultProcessor.format_for_response(tool_results)

        assert metadata["tool_call_count"] == 0
        assert metadata["tool_successes"] == 0
        assert metadata["tool_failures"] == 0
        assert metadata["tools_invoked"] == []
        assert metadata["tool_details"] == []

    def test_extract_citations_from_sources_array(self):
        """Test citation extraction from sources array."""
        tool_results = [
            {
                "tool": "web-scraper",
                "status": "success",
                "result": {
                    "sources": [
                        {
                            "title": "Example Page",
                            "url": "https://example.com",
                            "snippet": "Example content",
                        },
                        {
                            "title": "Another Page",
                            "url": "https://another.com",
                            "snippet": "More content",
                        },
                    ]
                },
            }
        ]

        citations = ToolResultProcessor.extract_citations_from_tools(tool_results)

        assert len(citations) == 2
        assert citations[0]["source_type"] == "tool"
        assert citations[0]["tool_name"] == "web-scraper"
        assert citations[0]["title"] == "Example Page"
        assert citations[0]["url"] == "https://example.com"
        assert citations[0]["snippet"] == "Example content"
        assert citations[1]["url"] == "https://another.com"

    def test_extract_citations_from_direct_url(self):
        """Test citation extraction from direct URL field."""
        tool_results = [
            {
                "tool": "web-scraper",
                "status": "success",
                "result": {
                    "url": "https://example.com",
                    "title": "Example Page",
                    "snippet": "Example content",
                },
            }
        ]

        citations = ToolResultProcessor.extract_citations_from_tools(tool_results)

        assert len(citations) == 1
        assert citations[0]["url"] == "https://example.com"
        assert citations[0]["title"] == "Example Page"

    def test_extract_citations_from_document_reference(self):
        """Test citation extraction from document reference."""
        tool_results = [
            {
                "tool": "document-retriever",
                "status": "success",
                "result": {
                    "document_id": "doc-123",
                    "document_url": "https://docs.example.com/doc-123",
                    "title": "Document Title",
                    "snippet": "Document snippet",
                },
            }
        ]

        citations = ToolResultProcessor.extract_citations_from_tools(tool_results)

        assert len(citations) == 1
        assert citations[0]["url"] == "https://docs.example.com/doc-123"
        assert citations[0]["title"] == "Document Title"

    def test_extract_citations_skips_errors(self):
        """Test that error results are skipped in citation extraction."""
        tool_results = [
            {
                "tool": "web-scraper",
                "status": "error",
                "error": "Connection failed",
            },
            {
                "tool": "database-query",
                "status": "success",
                "result": {"url": "https://example.com"},
            },
        ]

        citations = ToolResultProcessor.extract_citations_from_tools(tool_results)

        assert len(citations) == 1
        assert citations[0]["tool_name"] == "database-query"

    def test_extract_citations_no_citable_content(self):
        """Test citation extraction with no citable content."""
        tool_results = [
            {
                "tool": "calculator",
                "status": "success",
                "result": {"answer": 42},
            }
        ]

        citations = ToolResultProcessor.extract_citations_from_tools(tool_results)

        assert len(citations) == 0

    def test_normalize_execution_result_success(self):
        """Test normalizing successful execution result."""
        exec_result = {"result": {"data": "test"}}

        normalized = ToolResultProcessor.normalize_execution_result(
            tool_name="test-tool",
            exec_result=exec_result,
            duration_ms=100.0,
        )

        assert normalized["tool"] == "test-tool"
        assert normalized["status"] == "success"
        assert normalized["result"] == {"data": "test"}
        assert normalized["duration_ms"] == 100.0

    def test_normalize_execution_result_error(self):
        """Test normalizing error execution result."""
        normalized = ToolResultProcessor.normalize_execution_result(
            tool_name="test-tool",
            exec_result=None,
            error="Tool execution failed",
            duration_ms=5000.0,
        )

        assert normalized["tool"] == "test-tool"
        assert normalized["status"] == "error"
        assert normalized["error"] == "Tool execution failed"
        assert normalized["duration_ms"] == 5000.0

    def test_normalize_execution_result_dict_result(self):
        """Test normalizing dict result (not wrapped in 'result' key)."""
        exec_result = {"data": "test", "metadata": {"key": "value"}}

        normalized = ToolResultProcessor.normalize_execution_result(
            tool_name="test-tool",
            exec_result=exec_result,
        )

        assert normalized["status"] == "success"
        assert normalized["result"] == exec_result

    def test_normalize_execution_result_wrapped_result(self):
        """Test normalizing result wrapped in 'result' key."""
        exec_result = {"result": "simple_value"}

        normalized = ToolResultProcessor.normalize_execution_result(
            tool_name="test-tool",
            exec_result=exec_result,
        )

        assert normalized["status"] == "success"
        assert normalized["result"] == "simple_value"

    def test_normalize_execution_result_none(self):
        """Test normalizing None result."""
        normalized = ToolResultProcessor.normalize_execution_result(
            tool_name="test-tool",
            exec_result=None,
        )

        assert normalized["status"] == "success"
        assert normalized["result"] is None

    def test_format_for_llm_complex_nested_result(self):
        """Test formatting complex nested result structure."""
        tool_results = [
            {
                "tool": "complex-tool",
                "status": "success",
                "result": {
                    "nested": {
                        "deep": {
                            "value": "test",
                            "array": [1, 2, 3],
                        }
                    }
                },
            }
        ]

        formatted = ToolResultProcessor.format_for_llm(tool_results)

        assert "Tool: complex-tool" in formatted
        assert "nested" in formatted
        assert "deep" in formatted
        assert "test" in formatted
        assert "array" in formatted

    def test_format_for_response_missing_fields(self):
        """Test formatting response with missing optional fields."""
        tool_results = [
            {
                "tool": "test-tool",
                "status": "success",
                # Missing duration_ms
            }
        ]

        metadata = ToolResultProcessor.format_for_response(tool_results)

        assert metadata["tool_call_count"] == 1
        assert metadata["tool_details"][0]["duration_ms"] is None

    def test_format_for_llm_unknown_tool_name(self):
        """Test formatting with missing tool name."""
        tool_results = [
            {
                "status": "success",
                "result": {"data": "test"},
                # Missing tool name
            }
        ]

        formatted = ToolResultProcessor.format_for_llm(tool_results)

        assert "Tool: unknown" in formatted or "Tool:" in formatted
