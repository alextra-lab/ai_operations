"""
Integration tests for template-driven streaming functionality.

This module tests the B3-F3 feature: Streaming Per Template, which implements
streaming precedence rules based on use case configuration and intent types.
"""

from unittest.mock import MagicMock

import pytest

from src.orchestrator.app.orchestrator.controller import Orchestrator
from src.orchestrator.app.schemas.intent import RequestType
from src.orchestrator.app.schemas.use_case_config import PolicyConfig, UseCaseConfig


class TestTemplateStreaming:
    """Test template-driven streaming behavior."""

    def create_orchestrator(self):
        """Create orchestrator instance for testing with minimal setup."""

        config = {
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        mock_db = MagicMock()

        # Create orchestrator with minimal mocking
        orchestrator = Orchestrator(db=mock_db, config=config)

        # Mock the dependencies that require external services
        orchestrator.intent_parser = MagicMock()
        orchestrator.prompt_assembler = MagicMock()
        orchestrator.response_formatter = MagicMock()
        orchestrator.llm_router = MagicMock()

        return orchestrator

    @pytest.fixture
    def use_case_config_streaming_enabled(self):
        """Use case config with streaming enabled by default."""
        return UseCaseConfig(policy=PolicyConfig(streaming_default=True))

    @pytest.fixture
    def use_case_config_streaming_disabled(self):
        """Use case config with streaming disabled by default."""
        return UseCaseConfig(policy=PolicyConfig(streaming_default=False))

    def test_template_streaming_default_true(self, use_case_config_streaming_enabled):
        """Template streaming_default=True should enable streaming when no explicit flag."""
        orchestrator = self.create_orchestrator()

        # Test with no explicit stream parameter (None)
        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None,
            use_case_config=use_case_config_streaming_enabled,
            intent_type=RequestType.QUERY,
        )
        assert result is True

    def test_template_streaming_default_false(self, use_case_config_streaming_disabled):
        """Template streaming_default=False should disable streaming when no explicit flag."""
        orchestrator = self.create_orchestrator()

        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None,
            use_case_config=use_case_config_streaming_disabled,
            intent_type=RequestType.QUERY,
        )
        assert result is False

    def test_explicit_stream_overrides_template(self, use_case_config_streaming_enabled):
        """Explicit stream flag should override template default."""
        orchestrator = self.create_orchestrator()

        # Template says streaming=True, but explicit says False
        result = orchestrator._determine_streaming_behavior(
            explicit_stream=False,
            use_case_config=use_case_config_streaming_enabled,
            intent_type=RequestType.QUERY,
        )
        assert result is False

        # Template says streaming=False, but explicit says True
        result = orchestrator._determine_streaming_behavior(
            explicit_stream=True,
            use_case_config=UseCaseConfig(policy=PolicyConfig(streaming_default=False)),
            intent_type=RequestType.QUERY,
        )
        assert result is True

    def test_summarization_defaults_to_streaming(self, use_case_config_streaming_disabled):
        """SUMMARIZATION intent should default to streaming=True when no template config."""
        orchestrator = self.create_orchestrator()

        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None,
            use_case_config=use_case_config_streaming_disabled,
            intent_type=RequestType.SUMMARIZATION,
        )
        assert result is True

    def test_summarization_template_override(self):
        """SUMMARIZATION intent should respect template default when explicitly set."""
        orchestrator = self.create_orchestrator()

        # Template explicitly sets streaming=False for summarization
        config = UseCaseConfig(policy=PolicyConfig(streaming_default=False))

        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None, use_case_config=config, intent_type=RequestType.SUMMARIZATION
        )
        assert result is False

    def test_other_intents_default_to_no_streaming(self):
        """Other intent types should default to streaming=False when no config."""
        orchestrator = self.create_orchestrator()
        config = UseCaseConfig()  # Default config

        for intent_type in [RequestType.QUERY, RequestType.ENRICHMENT]:
            result = orchestrator._determine_streaming_behavior(
                explicit_stream=None, use_case_config=config, intent_type=intent_type
            )
            assert result is False

    def test_streaming_precedence_order(self):
        """Test that precedence order is correct: explicit > template > intent > global."""
        orchestrator = self.create_orchestrator()
        config_streaming_true = UseCaseConfig(policy=PolicyConfig(streaming_default=True))
        config_streaming_false = UseCaseConfig(policy=PolicyConfig(streaming_default=False))

        # Test precedence 1: Explicit flag overrides everything
        result = orchestrator._determine_streaming_behavior(
            explicit_stream=True,
            use_case_config=config_streaming_false,  # Template says False
            intent_type=RequestType.QUERY,  # Not SUMMARIZATION
        )
        assert result is True

        # Test precedence 2: Template default when no explicit flag
        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None,
            use_case_config=config_streaming_true,  # Template says True
            intent_type=RequestType.QUERY,  # Not SUMMARIZATION
        )
        assert result is True

        # Test precedence 3: Intent default (SUMMARIZATION) when no template
        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None,
            use_case_config=UseCaseConfig(),  # Default config (no streaming_default set)
            intent_type=RequestType.SUMMARIZATION,
        )
        assert result is True

        # Test precedence 4: Global default (False) when nothing else applies
        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None,
            use_case_config=UseCaseConfig(),  # Default config
            intent_type=RequestType.QUERY,  # Not SUMMARIZATION
        )
        assert result is False

    def test_edge_case_none_stream_parameter(self):
        """Test edge case where stream parameter is explicitly None."""
        orchestrator = self.create_orchestrator()
        config = UseCaseConfig(policy=PolicyConfig(streaming_default=True))

        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None, use_case_config=config, intent_type=RequestType.QUERY
        )
        assert result is True  # Should use template default

    def test_edge_case_config_without_policy(self):
        """Test edge case where config doesn't have policy attribute."""
        orchestrator = self.create_orchestrator()

        # Create config without policy
        config = UseCaseConfig()
        # Remove policy attribute to test edge case
        delattr(config, "policy")

        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None, use_case_config=config, intent_type=RequestType.SUMMARIZATION
        )
        assert result is True  # Should fall back to intent default (SUMMARIZATION)
