"""
Summary generation service for client-provided conversation data (ADR-031).

Generates executive summaries from client-provided conversation exports
without storing content server-side.
"""

from datetime import UTC, datetime
from typing import Any

from shared.logging_utils.fastapi import configure_logging

from ..schemas.summaries import (
    ConversationMessage,
    RedactionConfig,
    SummaryResponse,
)

logger = configure_logging(service_name="summary_service")


class SummaryService:
    """
    Service for generating summaries from client-provided conversation data.

    This service implements ADR-031 (Client-Owned Exports) by generating
    summaries on-demand from client data without server-side storage.
    """

    def __init__(self, db: Any = None):
        """
        Initialize summary service.

        Args:
            db: Database session (for future use, not used in stateless v1)
        """
        self.db = db

    async def generate(
        self,
        use_case_id: str,
        messages: list[ConversationMessage],
        export_format: str = "markdown",
        redaction: RedactionConfig | None = None,
        max_summary_tokens: int = 500,  # noqa: ARG002 - reserved for v2+
        include_metadata: bool = False,  # noqa: ARG002 - reserved for v2+
    ) -> SummaryResponse:
        """
        Generate summary from conversation messages.

        Args:
            use_case_id: Use case identifier for context
            messages: List of conversation messages
            export_format: Output format (text, markdown, json)
            redaction: PII/secret redaction configuration
            max_summary_tokens: Maximum summary length in tokens
            include_metadata: Include conversation metadata in summary

        Returns:
            SummaryResponse with generated summary and metadata
        """
        # Convert ConversationMessage objects to dictionaries for internal processing
        messages_dict = [msg.model_dump() for msg in messages]

        # Generate summary text
        conversation_text = self._format_messages_for_summarization(messages_dict)
        summary_text = await self._generate_executive_summary(
            conversation_text, {"id": use_case_id, "name": use_case_id}
        )

        # Apply redaction if configured
        redacted_fields: list[str] = []
        if redaction:
            summary_text, redacted_fields = self._apply_redaction(summary_text, redaction)

        # Estimate token count (rough approximation: 1 token ~= 4 characters)
        token_count = len(summary_text) // 4

        logger.info(
            "Generated summary",
            extra={
                "use_case_id": use_case_id,
                "message_count": len(messages),
                "format": export_format,
                "token_count": token_count,
            },
        )

        return SummaryResponse(
            summary=summary_text,
            redacted_fields=redacted_fields,
            token_count=token_count,
            message_count=len(messages),
            format=export_format,
            generated_at=datetime.now(UTC).isoformat(),
            model_used="extraction-based-v1",  # v1 uses extraction, v2+ will use LLM
        )

    def _format_messages_for_summarization(self, messages: list[dict[str, Any]]) -> str:
        """Format messages for LLM summarization."""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"{role.upper()}: {content}")
        return "\n\n".join(lines)

    async def _generate_executive_summary(
        self, conversation_text: str, use_case_context: dict[str, Any]
    ) -> str:
        """
        Generate executive summary.

        For stateless v1, this provides a basic extraction-based summary.
        Future v2+ can use LLM for more sophisticated summarization.
        """
        # In v1, provide basic summary
        # In v2+, use LLM client for sophisticated summarization
        lines = conversation_text.split("\n\n")
        if len(lines) <= 3:
            return conversation_text

        # Extract first user query and last assistant response
        first_query = lines[0] if lines else ""
        last_response = lines[-1] if lines else ""

        return (
            f"This conversation involved {len(lines)} exchanges "
            f"using the {use_case_context.get('name', 'Unknown')} use case.\n\n"
            f"Initial query: {first_query[:200]}...\n\n"
            f"Final response: {last_response[:200]}..."
        )

    async def _generate_technical_summary(
        self, conversation_text: str, use_case_context: dict[str, Any]
    ) -> str:
        """Generate technical summary with implementation details."""
        # Basic technical summary for v1
        return (
            f"Technical Summary:\n\n"
            f"Use Case: {use_case_context.get('name', 'Unknown')}\n"
            f"Conversation Length: {len(conversation_text.split())} words\n"
            f"Exchanges: {conversation_text.count('USER:')}\n\n"
            f"Conversation Content:\n{conversation_text[:500]}..."
        )

    async def _generate_brief_summary(
        self,
        conversation_text: str,
        use_case_context: dict[str, Any],  # noqa: ARG002
    ) -> str:
        """Generate brief one-paragraph summary."""
        # Extract first few lines
        lines = conversation_text.split("\n\n")[:2]
        return " ".join(lines)

    def _apply_redaction(
        self, text: str, redaction_config: RedactionConfig
    ) -> tuple[str, list[str]]:
        """
        Apply redaction to text based on configuration.

        Args:
            text: Text to redact
            redaction_config: Redaction configuration

        Returns:
            Tuple of (redacted_text, list_of_redacted_field_types)
        """
        redacted_fields = []

        # In v1, provide basic redaction
        # v2+ can integrate with LLM-Guard for sophisticated redaction
        if redaction_config.pii:
            # Basic email redaction
            import re

            if re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text):
                text = re.sub(
                    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                    "[REDACTED_EMAIL]",
                    text,
                )
                redacted_fields.append("email")

        if redaction_config.secrets:
            # Basic API key redaction
            import re

            if re.search(r"(?i)(api[_-]?key|token)['\"]?\s*[:=]\s*['\"]?[\w-]+", text):
                text = re.sub(
                    r"(?i)(api[_-]?key|token)['\"]?\s*[:=]\s*['\"]?[\w-]+",
                    r"\1=[REDACTED]",
                    text,
                )
                redacted_fields.append("api_key")

        return text, redacted_fields
