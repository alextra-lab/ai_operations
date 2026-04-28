"""
Unit tests for configuration validation rules.
"""

from src.orchestrator.app.services.validation import ValidationSeverity
from src.orchestrator.app.services.validation.config_rules import (
    MaxTokensForPatternRule,
    RAGWithoutCollectionsRule,
    ReActWithoutToolStepsRule,
    StrictOutputWithoutSchemaRule,
)


class TestMaxTokensForPatternRule:
    """Tests for MaxTokensForPatternRule."""

    def test_insufficient_tokens_for_react(self):
        """Test detection of insufficient max_tokens for ReAct pattern."""
        rule = MaxTokensForPatternRule()
        use_case = {
            "metadata_json": {"pattern_id": "react"},
            "config_json": {"generation_params": {"max_tokens": 512}},
        }

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.WARNING
        assert "2048" in issues[0].message  # Recommended value
        assert issues[0].auto_fix is not None

    def test_sufficient_tokens_for_react(self):
        """Test that sufficient max_tokens pass validation."""
        rule = MaxTokensForPatternRule()
        use_case = {
            "metadata_json": {"pattern_id": "react"},
            "config_json": {"generation_params": {"max_tokens": 2048}},
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0

    def test_no_pattern_id(self):
        """Test that missing pattern_id is handled gracefully."""
        rule = MaxTokensForPatternRule()
        use_case = {
            "metadata_json": {},
            "config_json": {"generation_params": {"max_tokens": 512}},
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0


class TestReActWithoutToolStepsRule:
    """Tests for ReActWithoutToolStepsRule."""

    def test_react_without_tool_steps(self):
        """Test detection of ReAct pattern without max_tool_steps."""
        rule = ReActWithoutToolStepsRule()
        use_case = {
            "metadata_json": {"pattern_id": "react"},
            "config_json": {"generation_params": {}, "tools_allowlist": []},
        }

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.ERROR
        assert "max_tool_steps" in issues[0].message.lower()
        assert issues[0].auto_fix is not None

    def test_tools_enabled_without_max_steps(self):
        """Test detection of tools without max_tool_steps."""
        rule = ReActWithoutToolStepsRule()
        use_case = {
            "metadata_json": {"pattern_id": "zero-shot"},
            "config_json": {
                "generation_params": {},
                "tools_allowlist": ["search", "calculator"],
            },
        }

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert "max_tool_steps" in issues[0].message.lower()

    def test_react_with_tool_steps(self):
        """Test that ReAct with max_tool_steps passes."""
        rule = ReActWithoutToolStepsRule()
        use_case = {
            "metadata_json": {"pattern_id": "react"},
            "config_json": {
                "generation_params": {"max_tool_steps": 5},
                "tools_allowlist": ["search"],
            },
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0

    def test_no_tools_no_issue(self):
        """Test that no tools and not ReAct pattern passes."""
        rule = ReActWithoutToolStepsRule()
        use_case = {
            "metadata_json": {"pattern_id": "zero-shot"},
            "config_json": {"generation_params": {}, "tools_allowlist": []},
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0


class TestStrictOutputWithoutSchemaRule:
    """Tests for StrictOutputWithoutSchemaRule."""

    def test_strict_without_schema(self):
        """Test detection of STRICT mode without output_schema."""
        rule = StrictOutputWithoutSchemaRule()
        use_case = {
            "config_json": {"output_contract": {"validation_mode": "strict", "output_schema": None}}
        }

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.ERROR
        assert "strict" in issues[0].message.lower()
        assert "schema" in issues[0].message.lower()

    def test_strict_with_schema(self):
        """Test that STRICT mode with schema passes."""
        rule = StrictOutputWithoutSchemaRule()
        use_case = {
            "config_json": {
                "output_contract": {
                    "validation_mode": "strict",
                    "output_schema": {"type": "object", "properties": {}},
                }
            }
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0

    def test_best_effort_without_schema(self):
        """Test that BEST_EFFORT mode doesn't require schema."""
        rule = StrictOutputWithoutSchemaRule()
        use_case = {
            "config_json": {
                "output_contract": {
                    "validation_mode": "best_effort",
                    "output_schema": None,
                }
            }
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0


class TestRAGWithoutCollectionsRule:
    """Tests for RAGWithoutCollectionsRule."""

    def test_rag_enabled_without_collections(self):
        """Test detection of RAG enabled without collections."""
        rule = RAGWithoutCollectionsRule()
        use_case = {"config_json": {"rag": {"enabled": True, "vector_collections": []}}}

        issues = rule.validate(use_case)

        assert len(issues) == 1
        assert issues[0].severity == ValidationSeverity.ERROR
        assert "rag" in issues[0].message.lower()
        assert "collection" in issues[0].message.lower()

    def test_rag_enabled_with_collections(self):
        """Test that RAG with collections passes."""
        rule = RAGWithoutCollectionsRule()
        use_case = {
            "config_json": {"rag": {"enabled": True, "vector_collections": ["threat-intel"]}}
        }

        issues = rule.validate(use_case)

        assert len(issues) == 0

    def test_rag_disabled(self):
        """Test that disabled RAG passes validation."""
        rule = RAGWithoutCollectionsRule()
        use_case = {"config_json": {"rag": {"enabled": False, "vector_collections": []}}}

        issues = rule.validate(use_case)

        assert len(issues) == 0
