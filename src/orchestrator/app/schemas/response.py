"""
Response Formatter Schema for AI Operations Platform.

This module defines the schema models for the Response Formatter component,
which returns structured JSON payloads with responses, source citations,
confidence scores, and suggested actions.

The Response Formatter is the final component in the orchestrator workflow:
Intent Parser → Retrieval Engine → Prompt Assembler → Tool & Model Router → LLM Router → Response Formatter
"""

from typing import Any

from pydantic import BaseModel, Field

from .visualization_spec import VisualizationSpec


class SourceMetadata(BaseModel):
    """
    Model for tracking source information in responses.

    Contains metadata about sources used in retrieval-augmented generation.
    Schema matches frontend TypeScript interface for proper display.
    """

    document_id: str = Field(
        ..., description="Unique identifier for the source document", min_length=1
    )
    title: str = Field(..., description="Title or name of the source document", min_length=1)
    source: str = Field(
        ...,
        description="Source system or origin (e.g., 'Document Library', 'Threat Intel')",
        min_length=1,
    )
    author: str | None = Field(None, description="Document author if available")
    similarity_score: float = Field(
        ...,
        description="Similarity score from vector search (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    page_number: int | None = Field(None, description="Page number if applicable")
    chunk_text: str | None = Field(None, description="Full chunk text content")
    content: str | None = Field(None, description="Chunk content (alias for chunk_text)")
    chunk_index: int = Field(..., description="Index of the chunk within the document", ge=0)
    document_type: str = Field(..., description="Document file type (pdf, docx, txt, etc.)")
    classification: str | None = Field(None, description="Document classification level")
    created_at: str = Field(..., description="Document creation timestamp")
    url: str | None = Field(None, description="URL to access the document if available")


class RetrievalMetrics(BaseModel):
    """
    Metrics related to retrieval-augmented generation (RAG) performance.

    Contains comprehensive statistics about document retrieval, similarity scores,
    and search effectiveness for the current query.
    """

    top_k: int = Field(..., description="Number of documents requested for retrieval", ge=0)
    hits: int = Field(..., description="Number of documents actually retrieved", ge=0)
    avg_similarity: float = Field(
        ...,
        description="Average similarity score across all retrieved documents",
        ge=0.0,
        le=1.0,
    )
    min_similarity: float = Field(
        ...,
        description="Minimum similarity score among retrieved documents",
        ge=0.0,
        le=1.0,
    )
    max_similarity: float = Field(
        ...,
        description="Maximum similarity score among retrieved documents",
        ge=0.0,
        le=1.0,
    )
    source_count: int = Field(..., description="Number of unique source documents used", ge=0)


class GuardMetrics(BaseModel):
    """
    Metrics related to LLM-Guard security validation.

    Contains information about input sanitization, risk assessment,
    and security validation results.
    """

    risk_score: float = Field(
        ...,
        description="Overall risk score from LLM-Guard validation (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    modified: bool = Field(..., description="Whether the input was modified during validation")
    details: dict = Field(
        default_factory=dict, description="Detailed scanner results from LLM-Guard"
    )


class ModelMetrics(BaseModel):
    """
    Metrics related to LLM model usage and performance.

    Contains information about model selection, token usage,
    and generation performance.
    """

    model_id: str = Field(..., description="Identifier of the LLM model used for generation")
    tokens_in: int = Field(..., description="Number of input tokens processed", ge=0)
    tokens_out: int = Field(..., description="Number of output tokens generated", ge=0)
    total_tokens: int = Field(..., description="Total tokens used (input + output)", ge=0)
    processing_time: float = Field(
        ..., description="Time taken for LLM generation in seconds", ge=0.0
    )
    metadata: dict = Field(default_factory=dict, description="Additional model-specific metadata")


class ServiceStatus(BaseModel):
    """
    Service availability tracking for request processing.

    Indicates which backend services were actively used during request processing.
    This allows for transparent monitoring and debugging while maintaining
    consistent user experience regardless of service availability.
    """

    retrieval_active: bool = Field(..., description="Whether document retrieval was performed")
    guard_active: bool = Field(
        ..., description="Whether LLM-Guard security validation was performed"
    )
    model_active: bool = Field(..., description="Whether LLM model generation was performed")
    embedding_active: bool = Field(False, description="Whether embedding service was used")

    # Service health status
    retrieval_healthy: bool = Field(True, description="Retrieval service health at request time")
    guard_healthy: bool = Field(True, description="Guard service health at request time")
    model_healthy: bool = Field(True, description="Model service health at request time")


class ConsolidatedMetrics(BaseModel):
    """
    Comprehensive metrics consolidation for the entire request processing pipeline.

    All metric sub-objects are always present with safe default values when
    services are unavailable or disabled. This implements the Null Object Pattern
    for robust frontend handling and graceful degradation.

    Contains all metrics from retrieval, guard, and model components,
    plus a consolidated confidence score calculated using weighted factors.
    """

    retrieval: RetrievalMetrics = Field(
        default_factory=lambda: RetrievalMetrics(
            top_k=0,
            hits=0,
            avg_similarity=0.0,
            min_similarity=0.0,
            max_similarity=0.0,
            source_count=0,
        ),
        description="Retrieval-augmented generation metrics (always present, zero values if not used)",
    )
    guard: GuardMetrics = Field(
        default_factory=lambda: GuardMetrics(
            risk_score=0.0,
            modified=False,
            details={"status": "not_performed", "reason": "guard_disabled"},
        ),
        description="LLM-Guard security validation metrics (always present, safe values if disabled)",
    )
    model: ModelMetrics = Field(
        default_factory=lambda: ModelMetrics(
            model_id="none",
            tokens_in=0,
            tokens_out=0,
            total_tokens=0,
            processing_time=0.0,
            metadata={"status": "not_used"},
        ),
        description="LLM model usage metrics (always present, zero values if not used)",
    )
    confidence_score: float = Field(
        ...,
        description="Consolidated confidence score (0.0 to 1.0) calculated from weighted factors",
        ge=0.0,
        le=1.0,
    )
    calculation_method: str = Field(
        default="weighted_consolidation",
        description="Method used to calculate the consolidated confidence score",
    )
    service_status: ServiceStatus = Field(
        default_factory=lambda: ServiceStatus(
            retrieval_active=False,
            guard_active=False,
            model_active=False,
            embedding_active=False,
            retrieval_healthy=True,
            guard_healthy=True,
            model_healthy=True,
        ),
        description="Service availability tracking",
    )


class FormattedResponse(BaseModel):
    """
    Model for structured response output.

    Contains the formatted response text, source citations, confidence score,
    and comprehensive metrics. All metrics are always present with default
    values implementing the Null Object Pattern for robust error handling.
    """

    response: str = Field(..., description="The formatted response text", min_length=1)
    sources: list[SourceMetadata] = Field(
        default_factory=list,
        description="List of sources used in generating the response",
    )
    confidence: float = Field(
        ...,
        description="Overall confidence score for the response (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    metrics: ConsolidatedMetrics = Field(
        default_factory=lambda: ConsolidatedMetrics(
            retrieval=RetrievalMetrics(
                top_k=0,
                hits=0,
                avg_similarity=0.0,
                min_similarity=0.0,
                max_similarity=0.0,
                source_count=0,
            ),
            guard=GuardMetrics(risk_score=0.0, modified=False, details={}),
            model=ModelMetrics(
                model_id="none",
                tokens_in=0,
                tokens_out=0,
                total_tokens=0,
                processing_time=0.0,
                metadata={},
            ),
            confidence_score=0.0,
            service_status=ServiceStatus(
                retrieval_active=False,
                guard_active=False,
                model_active=False,
                embedding_active=False,
                retrieval_healthy=True,
                guard_healthy=True,
                model_healthy=True,
            ),
        ),
        description="Comprehensive metrics (always present, defaults if services unavailable)",
    )
    suggested_actions: dict = Field(
        default_factory=dict,
        description="Suggested next actions (empty dict if none available)",
    )
    request_id: str = Field(
        ...,
        description="Unique identifier for this request execution used for tracking and analytics",
    )
    cache_stats: dict | None = Field(
        None,
        description="Conversation cache utilization stats (tokens, turns, compression warnings)",
    )
    structured_data: dict[str, Any] | None = Field(
        default=None,
        description="Parsed structured output when output_contract.format is json/yaml/structured",
    )
    visualization_spec: VisualizationSpec | None = Field(
        default=None,
        description="Portable visualization spec (Vega-Lite + table) when template_id is configured (ADR-068)",
    )
