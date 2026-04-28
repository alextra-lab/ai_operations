"""
Unit tests for streaming precedence logic.

This module tests the core streaming precedence logic without requiring
full orchestrator initialization.
"""

from src.orchestrator.app.schemas.intent import RequestType
from src.orchestrator.app.schemas.use_case_config import PolicyConfig, UseCaseConfig


class TestStreamingPrecedence:
    """Test streaming precedence logic in isolation."""

    def create_mock_orchestrator(self):
        """Create a mock orchestrator with just the streaming logic."""

        # Create a mock orchestrator that only has the streaming method
        class MockOrchestrator:
            def _determine_streaming_behavior(
                self,
                explicit_stream: bool,
                use_case_config: UseCaseConfig,
                intent_type: RequestType,
            ) -> bool:
                """
                Determine streaming behavior based on precedence rules.

                Precedence order:
                1. Request flag (explicit stream parameter) - highest priority
                2. Template default (config.policy.streaming_default) - medium priority
                3. Intent default (SUMMARIZATION defaults to streaming=True) - lower priority
                4. Global default (stream=False) - lowest priority
                """
                # Priority 1: Explicit request flag overrides everything
                if explicit_stream is not None:
                    return explicit_stream

                # Priority 2: Template default from config (only if explicitly set)
                if (
                    hasattr(use_case_config, "policy")
                    and hasattr(use_case_config.policy, "streaming_default")
                    and use_case_config.policy.model_fields_set
                    and "streaming_default" in use_case_config.policy.model_fields_set
                ):
                    return use_case_config.policy.streaming_default

                # Priority 3: Intent-specific defaults
                # Priority 4: Global default
                return intent_type == RequestType.SUMMARIZATION

        return MockOrchestrator()

    def test_template_streaming_default_true(self):
        """Template streaming_default=True should enable streaming when no explicit flag."""
        orchestrator = self.create_mock_orchestrator()
        config = UseCaseConfig(policy=PolicyConfig(streaming_default=True))

        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None, use_case_config=config, intent_type=RequestType.QUERY
        )
        assert result is True

    def test_template_streaming_default_false(self):
        """Template streaming_default=False should disable streaming when no explicit flag."""
        orchestrator = self.create_mock_orchestrator()
        config = UseCaseConfig(policy=PolicyConfig(streaming_default=False))

        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None, use_case_config=config, intent_type=RequestType.QUERY
        )
        assert result is False

    def test_explicit_stream_overrides_template(self):
        """Explicit stream flag should override template default."""
        orchestrator = self.create_mock_orchestrator()
        config_streaming_true = UseCaseConfig(policy=PolicyConfig(streaming_default=True))
        config_streaming_false = UseCaseConfig(policy=PolicyConfig(streaming_default=False))

        # Template says streaming=True, but explicit says False
        result = orchestrator._determine_streaming_behavior(
            explicit_stream=False,
            use_case_config=config_streaming_true,
            intent_type=RequestType.QUERY,
        )
        assert result is False

        # Template says streaming=False, but explicit says True
        result = orchestrator._determine_streaming_behavior(
            explicit_stream=True,
            use_case_config=config_streaming_false,
            intent_type=RequestType.QUERY,
        )
        assert result is True

    def test_summarization_defaults_to_streaming(self):
        """SUMMARIZATION intent should default to streaming=True when no template config."""
        orchestrator = self.create_mock_orchestrator()
        # Use default config without explicit streaming_default
        config = UseCaseConfig()

        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None, use_case_config=config, intent_type=RequestType.SUMMARIZATION
        )
        assert result is True

    def test_summarization_template_override(self):
        """SUMMARIZATION intent should respect template default when explicitly set."""
        orchestrator = self.create_mock_orchestrator()
        config = UseCaseConfig(policy=PolicyConfig(streaming_default=False))

        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None, use_case_config=config, intent_type=RequestType.SUMMARIZATION
        )
        assert result is False  # Template default should override intent default

    def test_other_intents_default_to_no_streaming(self):
        """Other intent types should default to streaming=False when no config."""
        orchestrator = self.create_mock_orchestrator()
        config = UseCaseConfig()  # Default config

        for intent_type in [RequestType.QUERY, RequestType.ENRICHMENT]:
            result = orchestrator._determine_streaming_behavior(
                explicit_stream=None, use_case_config=config, intent_type=intent_type
            )
            assert result is False

    def test_streaming_precedence_order(self):
        """Test that precedence order is correct: explicit > template > intent > global."""
        orchestrator = self.create_mock_orchestrator()
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
        orchestrator = self.create_mock_orchestrator()
        config = UseCaseConfig(policy=PolicyConfig(streaming_default=True))

        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None, use_case_config=config, intent_type=RequestType.QUERY
        )
        assert result is True  # Should use template default

    def test_edge_case_config_without_policy(self):
        """Test edge case where config doesn't have policy attribute."""
        orchestrator = self.create_mock_orchestrator()

        # Create config without policy
        config = UseCaseConfig()
        # Remove policy attribute to test edge case
        delattr(config, "policy")

        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None, use_case_config=config, intent_type=RequestType.SUMMARIZATION
        )
        assert result is True  # Should fall back to intent default (SUMMARIZATION)

    def test_all_request_types(self):
        """Test streaming behavior for all request types."""
        orchestrator = self.create_mock_orchestrator()
        config = UseCaseConfig()  # Default config

        # Test all request types with default config
        for intent_type in RequestType:
            result = orchestrator._determine_streaming_behavior(
                explicit_stream=None, use_case_config=config, intent_type=intent_type
            )

            if intent_type == RequestType.SUMMARIZATION:
                assert result is True, "SUMMARIZATION should default to streaming=True"
            else:
                assert result is False, f"{intent_type} should default to streaming=False"

    def test_template_config_edge_cases(self):
        """Test edge cases with template configuration."""
        orchestrator = self.create_mock_orchestrator()

        # Test with explicit streaming=True in template
        config_true = UseCaseConfig(policy=PolicyConfig(streaming_default=True))
        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None, use_case_config=config_true, intent_type=RequestType.QUERY
        )
        assert result is True

        # Test with explicit streaming=False in template
        config_false = UseCaseConfig(policy=PolicyConfig(streaming_default=False))
        result = orchestrator._determine_streaming_behavior(
            explicit_stream=None,
            use_case_config=config_false,
            intent_type=RequestType.SUMMARIZATION,
        )
        assert result is False  # Template should override intent default
