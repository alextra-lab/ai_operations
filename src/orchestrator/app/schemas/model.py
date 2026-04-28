"""
Model Registry Schemas for AI Operations Platform.

This module defines schemas for the Model Registry service,
which tracks available AI/ML models and their capabilities.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelCapabilities(BaseModel):
    """Model capabilities and features."""

    supports_tools: bool = False
    supports_vision: bool = False
    supports_audio: bool = False
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_json_mode: bool = False


class ReasoningConfig(BaseModel):
    """Configuration for reasoning models."""

    max_thinking_tokens: int | None = Field(
        None, description="Maximum tokens for thinking/reasoning"
    )
    show_thinking: bool = Field(False, description="Whether to show reasoning process")
    thinking_budget: int | None = Field(None, description="Budget for reasoning tokens")


class TemperatureRange(BaseModel):
    """Valid temperature range for model."""

    min: float = Field(0.0, ge=0.0, le=2.0)
    max: float = Field(2.0, ge=0.0, le=2.0)


class ModelPricing(BaseModel):
    """Model pricing information."""

    input_price_per_million: Decimal | None = Field(
        None, description="Price per 1M input tokens in USD"
    )
    output_price_per_million: Decimal | None = Field(
        None, description="Price per 1M output tokens in USD"
    )
    currency: str = Field("USD", description="Currency code")


class ModelPerformance(BaseModel):
    """Model performance characteristics."""

    typical_latency_ms: int | None = Field(None, description="Typical response latency")
    tokens_per_second: float | None = Field(None, description="Generation speed")
    context_window: int | None = Field(None, description="Maximum context window")
    max_input_tokens: int | None = Field(None, description="Maximum input tokens")
    max_output_tokens: int | None = Field(None, description="Maximum output tokens")


class ModelBase(BaseModel):
    """Base model schema with common fields."""

    model_id: str = Field(..., description="API identifier for the model")
    name: str = Field(..., description="Human-readable model name")
    provider_type: str = Field(
        ..., description="Provider type (openai, azure, mistral, anthropic, local)"
    )
    provider: str | None = Field(
        None,
        description="Gateway provider instance name (e.g., LMStudio, MyOpenAI). NULL for local models.",
    )
    model_type: str = Field(..., description="Model type (llm, embedding, reasoning, etc.)")
    description: str | None = Field(None, description="Model description")


class ModelCreate(ModelBase):
    """Schema for creating a new model."""

    context_window: int | None = Field(None, ge=0)
    max_input_tokens: int | None = Field(None, ge=0)
    max_output_tokens: int | None = Field(None, ge=0)
    embedding_dimensions: int | None = Field(
        None, ge=0, description="Vector dimensions for embedding models"
    )
    supports_tools: bool = False
    supports_vision: bool = False
    supports_audio: bool = False
    is_reasoning_model: bool = False
    reasoning_config: dict[str, Any] | None = None
    typical_latency_ms: int | None = Field(None, ge=0)
    tokens_per_second: float | None = Field(None, ge=0)
    input_price_per_million: Decimal | None = Field(None, ge=0)
    output_price_per_million: Decimal | None = Field(None, ge=0)
    specialization: str | None = None
    version: str | None = None
    release_date: date | None = None
    default_temperature: Decimal = Field(Decimal("0.7"), ge=0, le=2)
    temperature_range: dict[str, float] | None = None
    recommended_use_cases: list[str] | None = None
    api_endpoint: str | None = None
    api_config: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None


class ModelUpdate(BaseModel):
    """Schema for updating a model."""

    name: str | None = None
    description: str | None = None
    provider: str | None = None
    context_window: int | None = Field(None, ge=0)
    max_input_tokens: int | None = Field(None, ge=0)
    max_output_tokens: int | None = Field(None, ge=0)
    embedding_dimensions: int | None = Field(None, ge=0)
    is_available: bool | None = None
    is_hidden: bool | None = None
    deprecated: bool | None = None
    health_status: str | None = None
    input_price_per_million: Decimal | None = Field(None, ge=0)
    output_price_per_million: Decimal | None = Field(None, ge=0)
    metadata_json: dict[str, Any] | None = None


class ModelResponse(ModelBase):
    """Schema for model response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    context_window: int | None
    max_input_tokens: int | None
    max_output_tokens: int | None
    embedding_dimensions: int | None
    supports_tools: bool
    supports_vision: bool
    supports_audio: bool
    is_reasoning_model: bool
    reasoning_config: dict[str, Any]
    typical_latency_ms: int | None
    tokens_per_second: float | None
    input_price_per_million: float | None
    output_price_per_million: float | None
    specialization: str | None
    version: str | None
    release_date: date | None
    deprecated: bool
    deprecation_date: date | None
    default_temperature: float
    temperature_range: dict[str, float]
    recommended_use_cases: list[str] | None
    is_available: bool
    is_hidden: bool
    last_checked_at: datetime | None
    health_status: str
    created_at: datetime
    updated_at: datetime
    metadata_json: dict[str, Any]


class ModelListResponse(BaseModel):
    """Schema for paginated model list."""

    models: list[ModelResponse]
    total: int
    page: int
    size: int
    pages: int


class ModelDetailedResponse(ModelResponse):
    """Detailed model response with additional computed fields."""

    capabilities: ModelCapabilities
    pricing: ModelPricing | None
    performance: ModelPerformance
    estimated_cost_per_1k_tokens: Decimal | None


class ModelRecommendation(BaseModel):
    """Model recommendation for specific use case."""

    model_id: str
    name: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recommendation confidence")
    reasoning: str = Field(..., description="Why this model was recommended")
    estimated_cost: Decimal | None = Field(None, description="Estimated cost per query")
    estimated_latency_ms: int | None = Field(None, description="Estimated latency")
    capabilities_match: float = Field(
        ..., ge=0.0, le=1.0, description="How well capabilities match requirements"
    )


class ModelSelectionRequest(BaseModel):
    """Request for model recommendation."""

    use_case_type: str = Field(..., description="Type of use case (query, rule_generation, etc.)")
    requirements: dict[str, Any] = Field(default_factory=dict, description="Specific requirements")
    constraints: dict[str, Any] | None = Field(None, description="Constraints (budget, latency)")
    prefer_capabilities: list[str] | None = Field(None, description="Preferred capabilities")
