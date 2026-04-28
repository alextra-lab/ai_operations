"""
Pydantic schemas for pricing management and model configuration.

This module defines the request/response models for the pricing tier management
system, including CRUD operations and audit trail functionality.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, validator


class PricingTierBase(BaseModel):
    """Base schema for pricing tier data."""

    tier_key: str = Field(
        ...,
        description="Unique identifier combining plan size and model class (e.g., XS|Large)",
    )
    tier_name: str = Field(..., description="Display name for the pricing tier")
    plan_size: str = Field(..., description="Plan size: XS, S, M, L, XL")
    model_class: str = Field(..., description="Model class: Large, Small, Codestral/Llama")
    input_rate_per_1m: float = Field(
        ..., ge=0, description="Input token rate per million tokens in KEUR"
    )
    output_rate_per_1m: float = Field(
        ..., ge=0, description="Output token rate per million tokens in KEUR"
    )
    rate_limit_tpm: int = Field(..., ge=1, description="Maximum tokens per minute for this tier")
    description: str | None = Field(None, description="Optional description")
    is_active: bool = Field(True, description="Whether the tier is active")
    is_default: bool = Field(
        False,
        description="Whether this is the default tier for its plan/model combination",
    )

    @validator("tier_key")
    def validate_tier_key(cls, v: str) -> str:
        """Validate tier key format."""
        if not isinstance(v, str):
            raise ValueError("Tier key must be a string")
        if "|" not in v:
            raise ValueError("Tier key must contain | separator (e.g., XS|Large)")
        parts = v.split("|")
        if len(parts) != 2:
            raise ValueError("Tier key must have exactly one | separator")
        return v

    @validator("plan_size")
    def validate_plan_size(cls, v: str) -> str:
        """Validate plan size values."""
        valid_sizes = ["XS", "S", "M", "L", "XL"]
        if v not in valid_sizes:
            raise ValueError(f'Plan size must be one of: {", ".join(valid_sizes)}')
        return v

    @validator("model_class")
    def validate_model_class(cls, v: str) -> str:
        """Validate model class values."""
        valid_classes = ["Large", "Small", "Codestral/Llama"]
        if v not in valid_classes:
            raise ValueError(f'Model class must be one of: {", ".join(valid_classes)}')
        return v


class PricingTierCreate(PricingTierBase):
    """Schema for creating a new pricing tier."""


class PricingTierUpdate(BaseModel):
    """Schema for updating an existing pricing tier."""

    tier_name: str | None = Field(None, description="Display name for the pricing tier")
    input_rate_per_1m: float | None = Field(
        None, ge=0, description="Input token rate per million tokens in KEUR"
    )
    output_rate_per_1m: float | None = Field(
        None, ge=0, description="Output token rate per million tokens in KEUR"
    )
    rate_limit_tpm: int | None = Field(
        None, ge=1, description="Maximum tokens per minute for this tier"
    )
    description: str | None = Field(None, description="Optional description")
    is_active: bool | None = Field(None, description="Whether the tier is active")
    is_default: bool | None = Field(None, description="Whether this is the default tier")


class PricingTierResponse(PricingTierBase):
    """Schema for pricing tier response data."""

    id: UUID = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: UUID | None = Field(None, description="User who created this tier")
    updated_by: UUID | None = Field(None, description="User who last updated this tier")

    class Config:
        from_attributes = True


class ModelConfigBase(BaseModel):
    """Base schema for model configuration data."""

    model_id: str = Field(..., description="Unique model identifier (e.g., mistral-large-latest)")
    model_name: str = Field(..., description="Display name for the model")
    model_provider: str = Field(..., description="Model provider (e.g., mistral, openai, meta)")
    tokenizer_type: str = Field(
        ..., description="Tokenizer type (tiktoken, sentencepiece, huggingface)"
    )
    tokenizer_file_path: str | None = Field(None, description="Path to bundled tokenizer file")
    encoding_name: str | None = Field(
        None, description="Tokenizer encoding name (e.g., cl100k_base)"
    )
    default_pricing_tier_id: UUID | None = Field(
        None, description="Default pricing tier for this model"
    )
    supports_streaming: bool = Field(True, description="Whether the model supports streaming")
    max_context_tokens: int = Field(8192, ge=1, description="Maximum context tokens")
    description: str | None = Field(None, description="Optional description")
    is_active: bool = Field(True, description="Whether the model is active")
    is_available: bool = Field(True, description="Whether the model is currently available")

    @validator("model_id")
    def validate_model_id(cls, v: str) -> str:
        """Validate model ID format."""
        if not isinstance(v, str) or len(v.strip()) == 0:
            raise ValueError("Model ID must be a non-empty string")
        return v.strip()

    @validator("model_provider")
    def validate_model_provider(cls, v: str) -> str:
        """Validate model provider values."""
        valid_providers = [
            "mistral",
            "openai",
            "meta",
            "microsoft",
            "foundation",
            "anthropic",
        ]
        if v.lower() not in valid_providers:
            raise ValueError(f'Model provider must be one of: {", ".join(valid_providers)}')
        return v.lower()

    @validator("tokenizer_type")
    def validate_tokenizer_type(cls, v: str) -> str:
        """Validate tokenizer type values."""
        valid_types = ["tiktoken", "sentencepiece", "huggingface"]
        if v not in valid_types:
            raise ValueError(f'Tokenizer type must be one of: {", ".join(valid_types)}')
        return v


class ModelConfigCreate(ModelConfigBase):
    """Schema for creating a new model configuration."""


class ModelConfigUpdate(BaseModel):
    """Schema for updating an existing model configuration."""

    model_name: str | None = Field(None, description="Display name for the model")
    model_provider: str | None = Field(None, description="Model provider")
    tokenizer_type: str | None = Field(None, description="Tokenizer type")
    tokenizer_file_path: str | None = Field(None, description="Path to bundled tokenizer file")
    encoding_name: str | None = Field(None, description="Tokenizer encoding name")
    default_pricing_tier_id: UUID | None = Field(
        None, description="Default pricing tier for this model"
    )
    supports_streaming: bool | None = Field(
        None, description="Whether the model supports streaming"
    )
    max_context_tokens: int | None = Field(None, ge=1, description="Maximum context tokens")
    description: str | None = Field(None, description="Optional description")
    is_active: bool | None = Field(None, description="Whether the model is active")
    is_available: bool | None = Field(None, description="Whether the model is currently available")


class ModelConfigResponse(ModelConfigBase):
    """Schema for model configuration response data."""

    id: UUID = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: UUID | None = Field(None, description="User who created this configuration")
    updated_by: UUID | None = Field(None, description="User who last updated this configuration")

    class Config:
        from_attributes = True


class PricingAuditResponse(BaseModel):
    """Schema for pricing tier audit trail data."""

    id: UUID = Field(..., description="Audit entry identifier")
    pricing_tier_id: UUID = Field(..., description="Pricing tier that was changed")
    action: str = Field(
        ..., description="Type of change (CREATE, UPDATE, DELETE, ACTIVATE, DEACTIVATE)"
    )
    changed_by: UUID = Field(..., description="User who made the change")
    changed_at: datetime = Field(..., description="When the change was made")
    old_values: dict[str, Any] | None = Field(None, description="Values before the change")
    new_values: dict[str, Any] | None = Field(None, description="Values after the change")
    change_reason: str | None = Field(None, description="Reason for the change")

    class Config:
        from_attributes = True


class TokenRateMetrics(BaseModel):
    """Rate limit metrics for LLMaaS tier management."""

    model_id: str = Field(..., description="Model identifier")
    tokens_in_per_minute: float = Field(..., ge=0, description="Input tokens per minute")
    tokens_out_per_minute: float = Field(..., ge=0, description="Output tokens per minute")
    total_tokens_per_minute: float = Field(..., ge=0, description="Total tokens per minute")
    rate_limit_tpm: int = Field(..., ge=0, description="Rate limit from pricing tier")
    utilization_percentage: float = Field(..., ge=0, le=100, description="Utilization percentage")
    tier_name: str = Field(..., description="Pricing tier name (e.g., XS|Large)")
    recommended_action: str = Field(
        ..., description="Recommended action: OK, THROTTLE, UPGRADE_TIER"
    )

    @validator("recommended_action")
    def validate_recommended_action(cls, v: str) -> str:
        """Validate recommended action values."""
        valid_actions = ["OK", "THROTTLE", "UPGRADE_TIER"]
        if v not in valid_actions:
            raise ValueError(f'Recommended action must be one of: {", ".join(valid_actions)}')
        return v


class TokenRateResponse(BaseModel):
    """Response schema for token rate analytics."""

    metrics: list[TokenRateMetrics] = Field(..., description="Rate metrics for each model")
    window_minutes: int = Field(..., ge=1, description="Time window used for calculation")
    calculated_at: datetime = Field(
        default_factory=datetime.now, description="When the calculation was performed"
    )


class PricingTierListResponse(BaseModel):
    """Response schema for pricing tier list with pagination."""

    tiers: list[PricingTierResponse] = Field(..., description="List of pricing tiers")
    total_count: int = Field(..., description="Total number of tiers")
    active_count: int = Field(..., description="Number of active tiers")


class ModelConfigListResponse(BaseModel):
    """Response schema for model configuration list with pagination."""

    models: list[ModelConfigResponse] = Field(..., description="List of model configurations")
    total_count: int = Field(..., description="Total number of models")
    active_count: int = Field(..., description="Number of active models")


class ModelPriceCurrentResponse(BaseModel):
    """Current (active) per-model pricing."""

    model_id: str = Field(..., description="Model identifier")
    currency: str = Field("EUR", description="Currency for pricing")
    input_price_per_million: float = Field(..., ge=0)
    output_price_per_million: float = Field(..., ge=0)
    effective_from: datetime | None = Field(None, description="When this price became active")
    effective_to: datetime | None = Field(
        None, description="When this price stops being active (if scheduled)"
    )


class ModelPriceChangeRequest(BaseModel):
    """Request to change per-model pricing (creates a new history entry)."""

    input_price_per_million: float = Field(..., ge=0)
    output_price_per_million: float = Field(..., ge=0)
    effective_from: datetime | None = Field(
        None, description="UTC time when new price becomes active (default: now)"
    )
    change_reason: str | None = Field(None, description="Reason for change (optional)")


class ModelPriceHistoryEntry(BaseModel):
    """Historical entry for per-model pricing."""

    id: UUID
    model_uuid: UUID | None = Field(None, description="Internal model UUID")
    model_id: str | None = Field(None, description="External model identifier")
    input_price_per_million: float
    output_price_per_million: float
    effective_from: datetime
    effective_to: datetime | None
    changed_by_user_id: UUID | None
    change_reason: str | None
    created_at: datetime

    class Config:
        from_attributes = True
