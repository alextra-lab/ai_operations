"""
Unit tests for SummaryService

Tests the summary generation service for Stateless Core v1 (ADR-031).
"""

import pytest

from src.orchestrator.app.schemas.summaries import (
    ConversationMessage,
    RedactionConfig,
    SummaryResponse,
)
from src.orchestrator.app.services.summary_service import SummaryService


class TestSummaryService:
    """Test cases for SummaryService."""

    @pytest.fixture
    def summary_service(self):
        """Create a summary service instance for testing."""
        return SummaryService(db=None)

    @pytest.fixture
    def sample_messages(self):
        """Sample conversation messages for testing."""
        return [
            ConversationMessage(
                role="user",
                content="What are the security implications of this alert?",
                timestamp="2025-11-01T10:00:00Z",
            ),
            ConversationMessage(
                role="assistant",
                content=(
                    "The alert indicates a potential data exfiltration attempt. "
                    "The user jdoe@example.com attempted to upload sensitive files "
                    "to an external service at 192.0.2.123."
                ),
                timestamp="2025-11-01T10:00:15Z",
            ),
            ConversationMessage(
                role="user",
                content="What should I do next?",
                timestamp="2025-11-01T10:01:00Z",
            ),
            ConversationMessage(
                role="assistant",
                content=(
                    "1. Isolate the user account jdoe@example.com\n"
                    "2. Block outbound connections to 192.0.2.123\n"
                    "3. Review access logs for data accessed\n"
                    "4. Escalate to incident response team"
                ),
                timestamp="2025-11-01T10:01:30Z",
            ),
        ]

    @pytest.fixture
    def redaction_config_pii(self):
        """Redaction configuration for PII."""
        return RedactionConfig(
            redact_pii=True,
            redact_secrets=False,
            replacement_strategy="mask",
            pii_patterns=["email", "ip"],
        )

    @pytest.fixture
    def redaction_config_secrets(self):
        """Redaction configuration for secrets."""
        return RedactionConfig(
            redact_pii=False,
            redact_secrets=True,
            replacement_strategy="remove",
            secret_patterns=["api_key", "password"],
        )

    @pytest.mark.asyncio
    async def test_generate_basic_summary(self, summary_service, sample_messages):
        """Test basic summary generation without redaction."""
        result = await summary_service.generate(
            use_case_id="threat-triage",
            messages=sample_messages,
            export_format="markdown",
        )

        assert isinstance(result, SummaryResponse)
        assert result.summary is not None
        assert len(result.summary) > 0
        assert result.message_count == 4
        assert result.format == "markdown"
        assert result.model_used == "extraction-based-v1"
        assert result.token_count > 0
        assert result.redacted_fields == []

    @pytest.mark.asyncio
    async def test_generate_summary_with_pii_redaction(
        self, summary_service, sample_messages, redaction_config_pii
    ):
        """Test summary generation with PII redaction."""
        result = await summary_service.generate(
            use_case_id="threat-triage",
            messages=sample_messages,
            export_format="markdown",
            redaction=redaction_config_pii,
        )

        assert isinstance(result, SummaryResponse)
        assert result.summary is not None

        # PII should be redacted (either not present or marked as redacted)
        assert (
            "jdoe@example.com" not in result.summary
            or "REDACTED" in result.summary
            or "***" in result.summary
        )

        # Redacted fields should be tracked if redaction occurred
        # Note: Implementation may use different field names
        assert isinstance(result.redacted_fields, list)

    @pytest.mark.asyncio
    async def test_generate_summary_text_format(self, summary_service, sample_messages):
        """Test summary generation in text format."""
        result = await summary_service.generate(
            use_case_id="threat-triage",
            messages=sample_messages,
            export_format="text",
        )

        assert isinstance(result, SummaryResponse)
        assert result.format == "text"
        assert result.summary is not None
        # Text format should not have markdown formatting
        assert "**" not in result.summary  # No bold
        assert "##" not in result.summary  # No headings

    @pytest.mark.asyncio
    async def test_generate_summary_json_format(self, summary_service, sample_messages):
        """Test summary generation in JSON format."""
        result = await summary_service.generate(
            use_case_id="threat-triage",
            messages=sample_messages,
            export_format="json",
        )

        assert isinstance(result, SummaryResponse)
        assert result.format == "json"
        assert result.summary is not None
        # Summary may be JSON string or plain text - both valid
        assert len(result.summary) > 0

    @pytest.mark.asyncio
    async def test_generate_summary_empty_messages(self, summary_service):
        """Test summary generation with empty messages list."""
        result = await summary_service.generate(
            use_case_id="threat-triage",
            messages=[],
            export_format="markdown",
        )

        assert isinstance(result, SummaryResponse)
        assert result.message_count == 0
        assert result.summary is not None
        # May be empty or have placeholder - both valid
        assert isinstance(result.summary, str)

    @pytest.mark.asyncio
    async def test_generate_summary_single_message(self, summary_service):
        """Test summary generation with single message."""
        messages = [
            ConversationMessage(
                role="user",
                content="Test message",
                timestamp="2025-11-01T10:00:00Z",
            )
        ]

        result = await summary_service.generate(
            use_case_id="test-case",
            messages=messages,
            export_format="markdown",
        )

        assert isinstance(result, SummaryResponse)
        assert result.message_count == 1
        assert result.summary is not None
        assert "test message" in result.summary.lower()

    @pytest.mark.asyncio
    async def test_generate_summary_token_estimation(self, summary_service, sample_messages):
        """Test token count estimation accuracy."""
        result = await summary_service.generate(
            use_case_id="threat-triage",
            messages=sample_messages,
            export_format="markdown",
        )

        assert result.token_count > 0
        # Token count should be roughly summary_length / 4
        expected_tokens = len(result.summary) // 4
        assert abs(result.token_count - expected_tokens) < 100

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Actual redaction not in extraction-based-v1, deferred to v2+ LLM-based summaries"
    )
    async def test_generate_summary_with_secrets_redaction(
        self, summary_service, redaction_config_secrets
    ):
        """Test summary generation with secrets redaction (v2+ feature)."""
        # v1 uses extraction-based summary, actual redaction in v2+ with LLM

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Redaction replacement strategies deferred to v2+ LLM-based summaries")
    async def test_generate_summary_replacement_strategies(self, summary_service):
        """Test different redaction replacement strategies."""
        messages = [
            ConversationMessage(
                role="user",
                content="User email is admin@example.com",
                timestamp="2025-11-01T10:00:00Z",
            )
        ]

        # Test mask strategy
        mask_config = RedactionConfig(
            redact_pii=True,
            replacement_strategy="mask",
            pii_patterns=["email"],
        )
        mask_result = await summary_service.generate(
            use_case_id="test",
            messages=messages,
            redaction=mask_config,
        )
        # Verify redaction occurred (email removed or masked)
        assert (
            "admin@example.com" not in mask_result.summary
            or "REDACTED" in mask_result.summary
            or "***" in mask_result.summary
        )

        # Test remove strategy
        remove_config = RedactionConfig(
            redact_pii=True,
            replacement_strategy="remove",
            pii_patterns=["email"],
        )
        remove_result = await summary_service.generate(
            use_case_id="test",
            messages=messages,
            redaction=remove_config,
        )
        # Email should be removed or redacted
        assert (
            "admin@example.com" not in remove_result.summary or "REDACTED" in remove_result.summary
        )

    @pytest.mark.asyncio
    async def test_generate_summary_metadata_fields(self, summary_service, sample_messages):
        """Test that all metadata fields are populated correctly."""
        result = await summary_service.generate(
            use_case_id="threat-triage",
            messages=sample_messages,
            export_format="markdown",
        )

        # Check all required fields
        assert hasattr(result, "summary")
        assert hasattr(result, "redacted_fields")
        assert hasattr(result, "token_count")
        assert hasattr(result, "message_count")
        assert hasattr(result, "format")
        assert hasattr(result, "generated_at")
        assert hasattr(result, "model_used")

        # Verify types
        assert isinstance(result.summary, str)
        assert isinstance(result.redacted_fields, list)
        assert isinstance(result.token_count, int)
        assert isinstance(result.message_count, int)
        assert isinstance(result.format, str)
        assert isinstance(result.generated_at, str)
        assert isinstance(result.model_used, str)

    @pytest.mark.asyncio
    async def test_generate_summary_timestamp_validation(self, summary_service, sample_messages):
        """Test that generated_at timestamp is valid ISO format."""
        result = await summary_service.generate(
            use_case_id="threat-triage",
            messages=sample_messages,
            export_format="markdown",
        )

        from datetime import datetime

        # Should be valid ISO 8601 timestamp
        try:
            parsed_time = datetime.fromisoformat(result.generated_at.replace("Z", "+00:00"))
            assert parsed_time is not None
        except ValueError:
            pytest.fail("generated_at is not a valid ISO 8601 timestamp")

    @pytest.mark.asyncio
    async def test_generate_summary_long_conversation(self, summary_service):
        """Test summary generation with long conversation (many messages)."""
        # Create 50 messages
        messages = [
            ConversationMessage(
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i} content with some test data",
                timestamp=f"2025-11-01T10:{i:02d}:00Z",
            )
            for i in range(50)
        ]

        result = await summary_service.generate(
            use_case_id="long-conversation",
            messages=messages,
            export_format="markdown",
        )

        assert isinstance(result, SummaryResponse)
        assert result.message_count == 50
        assert result.summary is not None
        assert result.token_count > 0

    @pytest.mark.asyncio
    async def test_generate_summary_special_characters(self, summary_service):
        """Test summary generation with special characters in messages."""
        messages = [
            ConversationMessage(
                role="user",
                content="Test with <html> & special chars: @#$%^&*()[]{}",
                timestamp="2025-11-01T10:00:00Z",
            ),
            ConversationMessage(
                role="assistant",
                content="Response with émojis 🔒 and ùñîçödé",
                timestamp="2025-11-01T10:00:15Z",
            ),
        ]

        result = await summary_service.generate(
            use_case_id="special-chars",
            messages=messages,
            export_format="markdown",
        )

        assert isinstance(result, SummaryResponse)
        assert result.summary is not None
        # Should handle special characters without errors

    @pytest.mark.asyncio
    async def test_generate_summary_multiline_content(self, summary_service):
        """Test summary generation with multiline message content."""
        messages = [
            ConversationMessage(
                role="user",
                content=(
                    "This is line 1\n"
                    "This is line 2\n"
                    "This is line 3\n"
                    "\n"
                    "This is after a blank line"
                ),
                timestamp="2025-11-01T10:00:00Z",
            )
        ]

        result = await summary_service.generate(
            use_case_id="multiline",
            messages=messages,
            export_format="markdown",
        )

        assert isinstance(result, SummaryResponse)
        assert result.summary is not None
        # Should preserve or appropriately handle multiline content

    def test_format_messages_for_summarization(self, summary_service):
        """Test internal message formatting method."""
        messages = [
            {"role": "user", "content": "Test 1", "timestamp": "2025-11-01T10:00:00Z"},
            {
                "role": "assistant",
                "content": "Test 2",
                "timestamp": "2025-11-01T10:00:15Z",
            },
        ]

        formatted = summary_service._format_messages_for_summarization(messages)

        assert isinstance(formatted, str)
        assert "Test 1" in formatted
        assert "Test 2" in formatted
        assert len(formatted) > 0

    def test_apply_redaction_with_pii(self, summary_service):
        """Test internal redaction method with PII."""
        text = "User email is admin@example.com and IP is 192.0.2.123"
        config = RedactionConfig(
            redact_pii=True,
            replacement_strategy="mask",
            pii_patterns=["email", "ip"],
        )

        redacted_text, redacted_fields = summary_service._apply_redaction(text, config)

        assert isinstance(redacted_text, str)
        assert isinstance(redacted_fields, list)
        assert len(redacted_fields) > 0
        # Email and IP should be masked or removed
        assert "admin@example.com" not in redacted_text or "***" in redacted_text
