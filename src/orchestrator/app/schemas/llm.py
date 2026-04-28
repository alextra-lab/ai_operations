"""
LLM Router Schema for AI Operations Platform.

This module defines the schema models for the LLM Router component,
which constructs enterprise authentication connections to remote LLMaaS endpoints
and routes requests based on model preferences and fallback rules.

The LLM Router is a key component in the orchestrator workflow:
Intent Parser → Retrieval Engine → Prompt Assembler → Tool & Model Router → LLM Router → Response Formatter

This module provides two response models:
- LLMResponse: For standard, non-streaming responses (complete responses)
- LLMStreamResponse: For streaming responses (incremental chunks)
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ModelType(str, Enum):
    """
    Enumeration of intent-specific LLM models.

    These models are aligned with request types and represent the primary intended
    use case for each model configuration. Each model type has associated metadata
    about its capabilities and recommended use cases.

    Synced with RequestType enum and database intent_types table (ADR-069).
    """

    # Original system intents
    QUERY = "QUERY"  # Model optimized for general questions and information retrieval
    RULE_GENERATION = "RULE_GENERATION"  # Model optimized for creating detection rules
    SUMMARIZATION = "SUMMARIZATION"  # Model optimized for content summarization
    ENRICHMENT = "ENRICHMENT"  # Model optimized for threat intelligence enrichment

    # Extended system intents (added per migration 036)
    CLASSIFICATION = "CLASSIFICATION"  # Model optimized for categorization and labeling
    EXTRACTION = "EXTRACTION"  # Model optimized for structured data extraction
    GENERATION = "GENERATION"  # Model optimized for content or artifact generation
    ANALYSIS = "ANALYSIS"  # Model optimized for deep analysis and assessment
    THREAT_TRIAGE = "THREAT_TRIAGE"  # Model optimized for threat assessment
    CONTRACT_REVIEW = "CONTRACT_REVIEW"  # Model optimized for contract analysis
    COMPLIANCE_CHECK = "COMPLIANCE_CHECK"  # Model optimized for compliance verification

    @property
    def metadata(self) -> dict[str, Any]:
        """Return model metadata based on type."""
        metadata_mapping = {
            ModelType.QUERY: {
                "max_tokens": 2048,
                "default_temperature": 0.7,
                "strengths": ["fast_responses", "information_retrieval"],
                "description": "Optimized for general questions and information retrieval",
            },
            ModelType.RULE_GENERATION: {
                "max_tokens": 2048,
                "default_temperature": 0.2,
                "strengths": ["structured_output", "pattern_creation"],
                "description": "Optimized for creating detection rules with high precision",
            },
            ModelType.SUMMARIZATION: {
                "max_tokens": 2048,
                "default_temperature": 0.5,
                "strengths": ["content_condensation", "key_point_extraction"],
                "description": "Optimized for summarizing document content or incident data",
            },
            ModelType.ENRICHMENT: {
                "max_tokens": 2048,
                "default_temperature": 0.6,
                "strengths": [
                    "context_augmentation",
                    "threat_intelligence_integration",
                ],
                "description": "Optimized for enriching incidents with threat intelligence",
            },
            ModelType.CLASSIFICATION: {
                "max_tokens": 1024,
                "default_temperature": 0.2,
                "strengths": ["structured_output", "categorization"],
                "description": "Optimized for categorization and labeling tasks",
            },
            ModelType.EXTRACTION: {
                "max_tokens": 2048,
                "default_temperature": 0.1,
                "strengths": ["structured_output", "data_parsing"],
                "description": "Optimized for extracting structured data from unstructured content",
            },
            ModelType.GENERATION: {
                "max_tokens": 4096,
                "default_temperature": 0.8,
                "strengths": ["creativity", "content_creation"],
                "description": "Optimized for creative content or artifact generation",
            },
            ModelType.ANALYSIS: {
                "max_tokens": 3072,
                "default_temperature": 0.5,
                "strengths": ["reasoning", "deep_analysis"],
                "description": "Optimized for deep analysis and assessment tasks",
            },
            ModelType.THREAT_TRIAGE: {
                "max_tokens": 2048,
                "default_temperature": 0.2,
                "strengths": ["reasoning", "risk_assessment"],
                "description": "Optimized for threat assessment and prioritization",
            },
            ModelType.CONTRACT_REVIEW: {
                "max_tokens": 4096,
                "default_temperature": 0.4,
                "strengths": ["large_context", "extraction"],
                "description": "Optimized for contract analysis and key terms extraction",
            },
            ModelType.COMPLIANCE_CHECK: {
                "max_tokens": 2048,
                "default_temperature": 0.2,
                "strengths": ["structured_output", "verification"],
                "description": "Optimized for regulatory compliance verification",
            },
        }
        return metadata_mapping[self]


class LLMRequest(BaseModel):
    """
    Model for LLM processing requests.

    Contains the prompt to be processed by the LLM, optional model preference,
    and generation parameters like temperature and max_tokens.
    Supports both single-turn (prompt) and multi-turn (messages) conversations.
    """

    prompt: str = Field(
        "",
        description="The assembled prompt to be sent to the LLM (for single-turn queries)",
    )
    messages: list[dict[str, Any]] | None = Field(
        None, description="OpenAI-style messages array for multi-turn conversations"
    )
    model_preference: ModelType | None = Field(
        None,
        description="Preferred model to use (if not specified, will be determined by the router)",
    )
    temperature: float = Field(
        0.7,
        description="Sampling temperature for generation (higher = more random)",
        ge=0.0,
        le=1.0,
    )
    max_tokens: int = Field(
        1024,
        description="Maximum number of tokens to generate",
        gt=0,
        le=16384,  # Setting a reasonable upper bound
    )
    tools: list[dict[str, Any]] | None = Field(
        None, description="List of tools available to the model"
    )
    tool_choice: str | dict[str, Any] | None = Field(
        None,
        description="Tool choice strategy (e.g., 'auto', 'required', or specific tool)",
    )
    model_name_override: str | None = Field(
        None,
        description="Direct model name override from use case config (bypasses ModelType mapping)",
    )
    response_format: dict[str, Any] | None = Field(
        None,
        description=(
            "OpenAI-compatible response_format (e.g. "
            '{"type": "json_object"} or '
            '{"type": "json_schema", "json_schema": {...}}). '
            "Set automatically from output_contract when format is JSON."
        ),
    )


class LLMResponse(BaseModel):
    """
    Model for standard, non-streaming LLM processing response.

    Contains the complete generated response from the LLM, information about
    which model was used, token usage statistics, and processing time metrics.

    For streaming responses, use LLMStreamResponse instead.
    """

    response: str | None = Field(
        ...,
        description="The complete LLM-generated response (can be None if tool calls only)",
    )
    model_used: ModelType | str = Field(
        ..., description="Model that generated the response (type or registry ID)"
    )
    tokens_used: int = Field(
        ..., description="Token usage information for the request and response", gt=0
    )
    processing_time: float = Field(
        ..., description="Time taken to generate response in seconds", gt=0.0
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata about the LLM processing (e.g., retry attempts, fallbacks)",
    )
    tool_calls: list[dict[str, Any]] | None = Field(
        None, description="Tool calls generated by the model"
    )


class LLMStreamResponse(BaseModel):
    """
    Model for streaming LLM processing responses.

    Similar to LLMResponse but designed specifically for streaming chunks that
    may contain partial, incremental content. It has relaxed validation requirements
    to accommodate empty chunks that may occur during streaming.

    Additional streaming-specific fields are included to provide context about the
    streaming process, such as chunk number and completion status.
    """

    response: str = Field(
        ...,
        description="The current chunk content or accumulated content from LLM generation",
        min_length=0,  # Allow empty strings for streaming chunks
    )
    model_used: ModelType | str = Field(
        ..., description="Model that generated the response (type or registry ID)"
    )
    tokens_used: int = Field(..., description="Token usage information so far", gt=0)
    processing_time: float = Field(
        ..., description="Time taken to generate response so far in seconds", gt=0.0
    )
    chunk_number: int | None = Field(
        None, description="Current chunk number in the stream (if tracked)", ge=0
    )
    is_final: bool = Field(False, description="Whether this is the final chunk in the stream")
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata about the stream processing",
    )
    tool_calls: list[dict[str, Any]] | None = Field(
        None, description="Tool calls generated in this chunk (delta)"
    )
