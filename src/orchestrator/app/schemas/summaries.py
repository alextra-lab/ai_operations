"""
Summary generation schemas for Stateless Core v1

This module defines the request/response schemas for conversation summary generation.

Follows ADR-031: Client-Owned Exports & Summary Generation
"""

from typing import Any

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """Single message in a conversation."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="Message timestamp (ISO 8601)")
    metadata: dict[str, Any] | None = Field(None, description="Optional message metadata")


class RedactionConfig(BaseModel):
    """Configuration for PII/secret redaction."""

    pii: bool = Field(True, description="Redact PII (emails, phone numbers, names)")
    secrets: bool = Field(True, description="Redact secrets (API keys, tokens)")
    custom_patterns: list[str] = Field(
        default_factory=list, description="Custom regex patterns to redact"
    )


class SummaryRequest(BaseModel):
    """Request schema for summary generation."""

    use_case_id: str = Field(..., description="Use case ID for context")
    messages: list[ConversationMessage] = Field(
        ..., min_length=1, description="Conversation messages to summarize"
    )
    export_format: str = Field(
        default="markdown", description="Output format (text, markdown, json)"
    )
    redaction: RedactionConfig | None = Field(
        None, description="PII/secret redaction configuration"
    )
    max_summary_tokens: int = Field(
        default=500, ge=100, le=2000, description="Maximum summary length in tokens"
    )
    include_metadata: bool = Field(
        default=False, description="Include conversation metadata in summary"
    )


class SummaryResponse(BaseModel):
    """Response schema for summary generation."""

    summary: str = Field(..., description="Generated summary text")
    redacted_fields: list[str] = Field(
        default_factory=list, description="List of field types that were redacted"
    )
    token_count: int = Field(..., ge=0, description="Summary token count")
    message_count: int = Field(..., ge=0, description="Number of messages summarized")
    format: str = Field(..., description="Summary format (text, markdown, json)")
    generated_at: str = Field(..., description="Generation timestamp (ISO 8601)")
    model_used: str | None = Field(None, description="Model used for summarization")
