"""
Use Case Configuration Schema for AI Operations Platform.

This module defines the Pydantic schema models for use case configuration,
enabling template-driven behavior across the orchestrator system.

The UseCaseConfig schema provides comprehensive configuration for:
- Model selection and generation parameters
- RAG (Retrieval Augmented Generation) settings
- Output formatting and validation
- Telemetry and policy enforcement
- Tool allowlists and visibility controls

This schema is used to validate and structure the config_json field
in the use_cases database table, enabling the Use-Case-Driven pattern.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, validator

from shared.logging_utils.fastapi import get_logger

from .tool import UseCaseToolRestrictions

# Logger for high-entropy warnings
logger = get_logger(__name__)


class SamplingPreset(str, Enum):
    """
    Predefined sampling configurations for variance control.

    NOTE: LLMs are inherently stochastic (probabilistic). These presets
    control the *shape* of the probability distribution P(token|context),
    not eliminate variance entirely.

    - STRICT: Narrow distribution (temp=0.15, top_p=0.90) for high consistency
    - BALANCED: Moderate distribution (temp=0.65, top_p=0.95) for general use
    - CREATIVE: Broad distribution (temp=0.85, top_p=0.97) for exploratory tasks

    Architecture: These presets are part of the "stochastic core" wrapped by
    a "deterministic shell" of validators and policy enforcement.

    See: docs/architecture/CONSISTENCY_MODEL.md, docs/GLOSSARY.md
    """

    STRICT = "strict"  # High consistency, low variance
    BALANCED = "balanced"  # Good general-purpose default
    CREATIVE = "creative"  # Exploratory, varied outputs
    CUSTOM = "custom"  # User-defined (requires override permission)


class InputFieldType(str, Enum):
    """Supported input field types for dynamic form generation."""

    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    NUMBER = "number"
    CHECKBOX = "checkbox"
    DATE = "date"


class PIIRedactionMode(str, Enum):
    """PII redaction modes for policy enforcement."""

    NONE = "none"
    ANONYMIZE = "anonymize"
    REDACT = "redact"
    ENCRYPT = "encrypt"


class OutputFormat(str, Enum):
    """Supported output formats for response generation."""

    TEXT = "text"
    JSON = "json"
    YAML = "yaml"
    STRUCTURED = "structured"


class ValidationMode(str, Enum):
    """Output validation modes."""

    BEST_EFFORT = "best_effort"
    STRICT = "strict"


class InputFieldOption(BaseModel):
    """Option for select-type input fields."""

    value: str = Field(description="Internal value for the option")
    label: str = Field(description="User-visible label for the option")


class InputFieldConfig(BaseModel):
    """
    Configuration for a single dynamic input field.

    Input fields enable structured form generation in the UI, allowing
    use cases to define specific, typed inputs beyond freeform queries.

    When input_fields is empty, use case operates in conversational mode.
    When input_fields is populated, use case shows structured form first,
    then allows conversational refinement after initial execution.

    Input fields also serve as SECURITY BOUNDARIES by scoping RAG searches,
    tool calls, and conversation context to the user-provided input values.

    DESIGN NOTE: Future enhancement needed for "discovery mode" use cases where
    investigators need to follow related entities (e.g., incident → related incidents).
    This requires balancing strict isolation (security/compliance) vs. discovery
    workflows (threat hunting). See ADR-044 for detailed discussion.

    See: ADR-044 (Use Cases as Bounded Refinement Spaces)
    """

    name: str = Field(description="Field name (used as key in inputs dict)")
    type: InputFieldType = Field(description="Field type for UI rendering")
    label: str = Field(description="User-visible label for the field")
    description: str | None = Field(default=None, description="Help text shown to user")
    required: bool = Field(default=True, description="Whether field is required for execution")
    placeholder: str | None = Field(default=None, description="Placeholder text for input fields")
    default_value: str | None = Field(default=None, description="Default value for the field")
    options: list[InputFieldOption] | None = Field(
        default=None,
        description="Options for select fields (required if type=select)",
    )

    @validator("options")
    def validate_options_for_select(
        cls, v: list[InputFieldOption] | None, values: dict[str, Any]
    ) -> list[InputFieldOption] | None:
        """Select fields must have options."""
        if values.get("type") == InputFieldType.SELECT and (not v or len(v) == 0):
            raise ValueError("Select fields must have at least one option")
        return v


class VisibilityConfig(BaseModel):
    """Configuration for use case visibility and access control."""

    roles: list[str] = Field(
        default_factory=list, description="List of roles that can access this use case"
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags for categorization and filtering"
    )


class ModelsConfig(BaseModel):
    """
    Configuration for model selection and routing.

    ADR-069: Model selection is deterministic.
    - If llm is set, that model is used directly (use case pin).
    - If llm is None, the intent default from intent_model_defaults is used.
    """

    llm: str | None = Field(
        default=None,
        description="LLM model identifier to pin this use case to. "
        "None = use the intent default from admin configuration.",
        min_length=1,
    )
    # NOTE: Embedding model removed - determined by collection(s) at search time
    # System uses DEFAULT_EMBEDDING_MODEL from environment configuration


class GenerationParamsConfig(BaseModel):
    """Configuration for LLM generation parameters."""

    # Preset-based configuration (preferred)
    sampling_preset: SamplingPreset = Field(
        default=SamplingPreset.BALANCED, description="Predefined sampling configuration"
    )

    # Legacy/override fields (require CUSTOM preset for modifications)
    temperature: float | None = Field(
        default=None,  # Derived from preset if None
        description="Temperature override (requires CUSTOM preset)",
        ge=0.0,
        le=1.0,
    )
    max_tokens: int | None = Field(
        default=None,  # Derived from preset if None
        description="Max tokens override",
        gt=0,
        le=16384,
    )
    top_p: float | None = Field(
        default=None,  # Derived from preset if None
        description="Top-p override (requires CUSTOM preset)",
        ge=0.0,
        le=1.0,
    )

    # Policy constraints
    max_tool_steps: int | None = Field(
        default=None,
        description="Maximum tool invocation steps (for ReAct patterns)",
        ge=1,
        le=10,
    )
    tool_step_timeout: int = Field(
        default=30, description="Timeout per tool step (seconds)", ge=5, le=120
    )

    # Existing fields
    frequency_penalty: float = Field(
        default=0.0, description="Frequency penalty (-2.0 to 2.0)", ge=-2.0, le=2.0
    )
    presence_penalty: float = Field(
        default=0.0, description="Presence penalty (-2.0 to 2.0)", ge=-2.0, le=2.0
    )

    @validator("temperature", "top_p")
    def validate_custom_override(cls, v: float | None, values: dict[str, Any]) -> float | None:
        """Custom parameters require CUSTOM preset."""
        if v is not None and values.get("sampling_preset") != SamplingPreset.CUSTOM:
            raise ValueError(
                f"Parameter override requires sampling_preset='custom'. "
                f"Current preset: {values.get('sampling_preset')}"
            )
        return v

    def get_effective_params(self) -> dict[str, Any]:
        """
        Resolve effective parameters from preset + overrides.

        Returns a dictionary with concrete values for all generation parameters.
        """
        # Preset parameter mappings
        preset_params = {
            SamplingPreset.STRICT: {
                "temperature": 0.15,
                "top_p": 0.90,
                "max_tokens": 1024,
            },
            SamplingPreset.BALANCED: {
                "temperature": 0.65,
                "top_p": 0.95,
                "max_tokens": 2048,
            },
            SamplingPreset.CREATIVE: {
                "temperature": 0.85,
                "top_p": 0.97,
                "max_tokens": 4096,
            },
            SamplingPreset.CUSTOM: {
                "temperature": 0.7,  # Fallback defaults
                "top_p": 0.95,
                "max_tokens": 2048,
            },
        }

        # Start with preset values
        preset_values = preset_params[self.sampling_preset].copy()

        # Apply overrides if provided
        effective = {
            "temperature": (
                self.temperature if self.temperature is not None else preset_values["temperature"]
            ),
            "top_p": self.top_p if self.top_p is not None else preset_values["top_p"],
            "max_tokens": (
                self.max_tokens if self.max_tokens is not None else preset_values["max_tokens"]
            ),
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }

        # Add tool-specific params if present
        if self.max_tool_steps is not None:
            effective["max_tool_steps"] = self.max_tool_steps
        effective["tool_step_timeout"] = self.tool_step_timeout

        # High-entropy detection warning
        if (
            effective["temperature"] > 0.9
            and effective["top_p"] > 0.97
            and self.sampling_preset == SamplingPreset.CUSTOM
        ):
            logger.warning(
                "High-entropy configuration detected: temperature=%s, top_p=%s. "
                "This may cause repetition loops or inconsistent outputs.",
                effective["temperature"],
                effective["top_p"],
            )

        return effective


class RAGConfig(BaseModel):
    """Configuration for Retrieval Augmented Generation."""

    enabled: bool = Field(default=True, description="Whether RAG is enabled for this use case")
    vector_collections: list[str] = Field(
        default_factory=lambda: ["documents"],
        description="List of vector collections to search",
    )
    top_k: int = Field(default=10, description="Number of top documents to retrieve", gt=0, le=100)
    similarity_threshold: float = Field(
        default=0.6,
        description="Minimum similarity score for retrieval",
        ge=0.0,
        le=1.0,
    )
    hybrid_bm25: bool = Field(
        default=False, description="Whether to use hybrid BM25 + vector search"
    )
    metadata_filters: dict[str, Any] = Field(
        default_factory=dict, description="Metadata filters for document retrieval"
    )
    tags: list[str] = Field(default_factory=list, description="Tags to filter documents by")


class UserPromptTemplateConfig(BaseModel):
    """
    Configuration for user-facing prompt template with variable injection.

    Use {{variable_name}} placeholders in the template; at execution time
    they are replaced with the corresponding input field values. When
    user_prompt_template is None, the execution path uses legacy
    "field: value" concatenation (backward compatible).
    """

    template: str = Field(
        default="",
        description="User prompt template with {{variable}} placeholders",
    )
    variables: list[str] = Field(
        default_factory=list,
        description="Declared variables (auto-extracted from template if empty)",
    )
    fallback_mode: Literal["concatenate", "error"] = Field(
        default="concatenate",
        description=(
            "When an input is missing: concatenate leaves placeholder text, "
            "error raises (e.g. strict use cases)"
        ),
    )


class OutputContractConfig(BaseModel):
    """Configuration for output formatting and validation."""

    format: OutputFormat = Field(
        default=OutputFormat.TEXT, description="Output format for responses"
    )
    output_schema: dict[str, Any] | None = Field(
        default=None, description="JSON schema for structured output validation"
    )
    validation_mode: ValidationMode = Field(
        default=ValidationMode.BEST_EFFORT,
        description="How strictly to validate output format",
    )

    # P3-F5: Output formatting template
    template_id: str | None = Field(
        default=None,
        description="Output format template ID for visualization (P3-F5)",
    )

    # ADR-068: Full template definition (injected at runtime for viz spec generation)
    template_definition: dict[str, Any] | None = Field(
        default=None,
        description="Full template definition dict (injected at runtime, not stored)",
        exclude=True,
    )


class TelemetryConfig(BaseModel):
    """Configuration for telemetry and metrics collection."""

    required_metrics: list[str] = Field(
        default_factory=lambda: ["retrieval", "performance", "model"],
        description="List of required metrics to collect",
    )


class PolicyConfig(BaseModel):
    """Configuration for policy enforcement and behavior."""

    streaming_enabled: bool = Field(
        default=True, description="Whether streaming is enabled for this use case"
    )
    streaming_default: bool = Field(
        default=False, description="Default streaming behavior for requests"
    )
    history_persistence: bool = Field(default=True, description="Whether to persist query history")
    pii_redaction: PIIRedactionMode = Field(
        default=PIIRedactionMode.ANONYMIZE,
        description="PII redaction mode for responses",
    )
    allow_custom_sampling: bool = Field(
        default=False,
        description="Whether CUSTOM sampling preset is allowed (requires use_case_publisher role or higher)",
    )


class UseCaseConfig(BaseModel):
    """
    Complete use case configuration schema.

    This is the main schema that validates the config_json field
    in the use_cases database table. It provides comprehensive
    configuration for all aspects of use case execution.

    Use cases operate as bounded iterative refinement spaces (ADR-044):
    - input_fields empty: Conversational mode from start
    - input_fields populated: Structured form → response → conversational refinement
    """

    model_config = {
        "extra": "allow",  # Allow future extensions (changed from "forbid" per ADR-044)
        "validate_assignment": True,  # Validate on assignment
    }

    # OPTIONAL: Dynamic form fields (ADR-044)
    input_fields: list[InputFieldConfig] = Field(
        default_factory=list,
        description="Input fields for dynamic form generation. Empty array = conversational mode.",
    )

    # Optional user prompt template ({{variable}} placeholders). None = legacy concatenation.
    user_prompt_template: UserPromptTemplateConfig | None = Field(
        default=None,
        description="Optional user prompt template. If None, uses legacy concatenation.",
    )

    visibility: VisibilityConfig = Field(
        default_factory=VisibilityConfig,
        description="Visibility and access control configuration",
    )
    models: ModelsConfig = Field(
        default_factory=ModelsConfig,
        description="Model selection and routing configuration",
    )
    generation_params: GenerationParamsConfig = Field(
        default_factory=GenerationParamsConfig, description="LLM generation parameters"
    )
    rag: RAGConfig = Field(
        default_factory=RAGConfig,
        description="RAG configuration and retrieval settings",
    )
    tools_allowlist: list[str] = Field(
        default_factory=list, description="List of allowed tools for this use case"
    )
    # ADR-057: Security-based tool restrictions
    tool_restrictions: UseCaseToolRestrictions | None = Field(
        default=None,
        description="Security-based tool restrictions. If None, only tools_allowlist is used.",
    )
    output_contract: OutputContractConfig = Field(
        default_factory=OutputContractConfig,
        description="Output formatting and validation configuration",
    )
    telemetry: TelemetryConfig = Field(
        default_factory=TelemetryConfig,
        description="Telemetry and metrics configuration",
    )
    policy: PolicyConfig = Field(
        default_factory=PolicyConfig,
        description="Policy enforcement and behavior configuration",
    )

    @validator("tools_allowlist")
    def validate_tools_allowlist(cls, v: list[str]) -> list[str]:
        """Validate that tools_allowlist contains valid tool names."""
        if not isinstance(v, list):
            raise ValueError("tools_allowlist must be a list")

        # Basic validation - can be extended with known tool names
        for tool in v:
            if not isinstance(tool, str) or not tool.strip():
                raise ValueError("All tools in allowlist must be non-empty strings")

        return v

    @validator("rag")
    def validate_rag_config(cls, v: "RAGConfig") -> "RAGConfig":
        """Validate RAG configuration consistency."""
        if v.enabled and not v.vector_collections:
            raise ValueError("RAG enabled but no vector collections specified")

        if v.enabled and v.top_k <= 0:
            raise ValueError("RAG enabled but top_k must be positive")

        return v

    @classmethod
    def get_default_config(cls) -> "UseCaseConfig":
        """Return a default configuration instance."""
        return cls()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UseCaseConfig":
        """Create instance from dictionary."""
        return cls(**data)

    def merge_with(self, other: "UseCaseConfig") -> "UseCaseConfig":
        """
        Merge this config with another, with other taking precedence.

        This is useful for applying overrides or updates to configurations.
        """
        # Convert both to dict, merge, and create new instance
        self_dict = self.model_dump()
        other_dict = other.model_dump()

        # Deep merge - other values override self values
        merged = self._deep_merge(self_dict, other_dict)
        return UseCaseConfig.from_dict(merged)

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = UseCaseConfig._deep_merge(result[key], value)
            else:
                result[key] = value

        return result
