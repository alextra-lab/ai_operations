"""
Unit tests for UseCaseConfig schema validation.

Tests comprehensive validation of the UseCaseConfig Pydantic model,
including field validation, constraint checking, and edge cases.
"""

import pytest
from app.schemas.use_case_config import (
    GenerationParamsConfig,
    ModelsConfig,
    OutputContractConfig,
    OutputFormat,
    PIIRedactionMode,
    PolicyConfig,
    RAGConfig,
    SamplingPreset,
    TelemetryConfig,
    UseCaseConfig,
    UserPromptTemplateConfig,
    ValidationMode,
    VisibilityConfig,
)
from pydantic import ValidationError


class TestVisibilityConfig:
    """Test VisibilityConfig validation."""

    def test_default_visibility_config(self):
        """Test default visibility configuration."""
        config = VisibilityConfig()
        assert config.roles == []
        assert config.tags == []

    def test_visibility_config_with_data(self):
        """Test visibility configuration with data."""
        config = VisibilityConfig(
            roles=["analyst", "admin"], tags=["threat_hunting", "investigation"]
        )
        assert config.roles == ["analyst", "admin"]
        assert config.tags == ["threat_hunting", "investigation"]

    def test_visibility_config_empty_lists(self):
        """Test visibility configuration with empty lists."""
        config = VisibilityConfig(roles=[], tags=[])
        assert config.roles == []
        assert config.tags == []


class TestModelsConfig:
    """Test ModelsConfig validation."""

    def test_default_models_config(self):
        """Test default models configuration (None = no override, router picks by intent)."""
        config = ModelsConfig()
        assert config.llm is None
        # NOTE: embedding field removed - system-wide configuration

    def test_models_config_custom(self):
        """Test custom models configuration."""
        config = ModelsConfig(
            llm="gpt-4-turbo"
            # embedding removed - system-wide configuration
        )
        assert config.llm == "gpt-4-turbo"
        # NOTE: embedding field no longer exists

    def test_models_config_empty_llm_raises_error(self):
        """Test that empty LLM raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ModelsConfig(llm="")
        assert "String should have at least 1 character" in str(exc_info.value)


class TestGenerationParamsConfig:
    """Test GenerationParamsConfig validation."""

    def test_default_generation_params(self):
        """Test default generation parameters (ADR-023: uses balanced preset)."""
        config = GenerationParamsConfig()
        assert config.sampling_preset == SamplingPreset.BALANCED
        assert config.temperature is None  # Derived from preset
        assert config.max_tokens is None  # Derived from preset
        assert config.top_p is None  # Derived from preset
        assert config.frequency_penalty == 0.0
        assert config.presence_penalty == 0.0

        # Test effective params resolve correctly
        effective = config.get_effective_params()
        assert effective["temperature"] == 0.65  # From balanced preset
        assert effective["max_tokens"] == 2048
        assert effective["top_p"] == 0.95

    def test_generation_params_custom(self):
        """Test custom generation parameters (ADR-023: requires custom preset)."""
        config = GenerationParamsConfig(
            sampling_preset=SamplingPreset.CUSTOM,
            temperature=0.5,
            max_tokens=2048,
            top_p=0.9,
            frequency_penalty=0.1,
            presence_penalty=0.1,
        )
        assert config.sampling_preset == SamplingPreset.CUSTOM
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.top_p == 0.9
        assert config.frequency_penalty == 0.1
        assert config.presence_penalty == 0.1

    def test_temperature_out_of_range_raises_error(self):
        """Test that temperature out of range raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationParamsConfig(sampling_preset=SamplingPreset.CUSTOM, temperature=1.5)
        assert "Input should be less than or equal to 1" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            GenerationParamsConfig(sampling_preset=SamplingPreset.CUSTOM, temperature=-0.1)
        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_max_tokens_out_of_range_raises_error(self):
        """Test that max_tokens out of range raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationParamsConfig(sampling_preset=SamplingPreset.CUSTOM, max_tokens=0)
        assert "Input should be greater than 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            GenerationParamsConfig(sampling_preset=SamplingPreset.CUSTOM, max_tokens=20000)
        assert "Input should be less than or equal to 16384" in str(exc_info.value)


class TestRAGConfig:
    """Test RAGConfig validation."""

    def test_default_rag_config(self):
        """Test default RAG configuration."""
        config = RAGConfig()
        assert config.enabled is True
        assert config.vector_collections == ["documents"]
        assert config.top_k == 10
        assert config.similarity_threshold == 0.6
        assert config.hybrid_bm25 is False
        assert config.metadata_filters == {}
        assert config.tags == []

    def test_rag_config_custom(self):
        """Test custom RAG configuration."""
        config = RAGConfig(
            enabled=True,
            vector_collections=["documents", "threat_intel"],
            top_k=5,
            similarity_threshold=0.8,
            hybrid_bm25=True,
            metadata_filters={"classification": "secret"},
            tags=["malware", "apt"],
        )
        assert config.enabled is True
        assert config.vector_collections == ["documents", "threat_intel"]
        assert config.top_k == 5
        assert config.similarity_threshold == 0.8
        assert config.hybrid_bm25 is True
        assert config.metadata_filters == {"classification": "secret"}
        assert config.tags == ["malware", "apt"]

    def test_rag_config_disabled(self):
        """Test disabled RAG configuration."""
        config = RAGConfig(enabled=False)
        assert config.enabled is False
        # Other fields can have any values when disabled

    def test_top_k_out_of_range_raises_error(self):
        """Test that top_k out of range raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            RAGConfig(top_k=0)
        assert "Input should be greater than 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RAGConfig(top_k=200)
        assert "Input should be less than or equal to 100" in str(exc_info.value)

    def test_similarity_threshold_out_of_range_raises_error(self):
        """Test that similarity_threshold out of range raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            RAGConfig(similarity_threshold=-0.1)
        assert "Input should be greater than or equal to 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            RAGConfig(similarity_threshold=1.1)
        assert "Input should be less than or equal to 1" in str(exc_info.value)


class TestOutputContractConfig:
    """Test OutputContractConfig validation."""

    def test_default_output_contract(self):
        """Test default output contract configuration."""
        config = OutputContractConfig()
        assert config.format == OutputFormat.TEXT
        assert config.output_schema is None
        assert config.validation_mode == ValidationMode.BEST_EFFORT

    def test_output_contract_custom(self):
        """Test custom output contract configuration."""
        output_schema = {
            "type": "object",
            "required": ["rule_name", "rule_content"],
            "properties": {
                "rule_name": {"type": "string"},
                "rule_content": {"type": "string"},
            },
        }
        config = OutputContractConfig(
            format=OutputFormat.JSON,
            output_schema=output_schema,
            validation_mode=ValidationMode.STRICT,
        )
        assert config.format == OutputFormat.JSON
        assert config.output_schema == output_schema
        assert config.validation_mode == ValidationMode.STRICT


class TestTelemetryConfig:
    """Test TelemetryConfig validation."""

    def test_default_telemetry_config(self):
        """Test default telemetry configuration."""
        config = TelemetryConfig()
        assert config.required_metrics == ["retrieval", "performance", "model"]

    def test_telemetry_config_custom(self):
        """Test custom telemetry configuration."""
        config = TelemetryConfig(
            required_metrics=[
                "retrieval",
                "guard",
                "performance",
                "model",
                "confidence",
            ]
        )
        assert config.required_metrics == [
            "retrieval",
            "guard",
            "performance",
            "model",
            "confidence",
        ]


class TestPolicyConfig:
    """Test PolicyConfig validation."""

    def test_default_policy_config(self):
        """Test default policy configuration."""
        config = PolicyConfig()
        assert config.streaming_enabled is True
        assert config.streaming_default is False
        assert config.history_persistence is True
        assert config.pii_redaction == PIIRedactionMode.ANONYMIZE

    def test_policy_config_custom(self):
        """Test custom policy configuration."""
        config = PolicyConfig(
            streaming_enabled=False,
            streaming_default=True,
            history_persistence=False,
            pii_redaction=PIIRedactionMode.REDACT,
        )
        assert config.streaming_enabled is False
        assert config.streaming_default is True
        assert config.history_persistence is False
        assert config.pii_redaction == PIIRedactionMode.REDACT


class TestUseCaseConfig:
    """Test UseCaseConfig validation and functionality."""

    def test_default_use_case_config(self):
        """Test default use case configuration."""
        config = UseCaseConfig()
        assert isinstance(config.visibility, VisibilityConfig)
        assert isinstance(config.models, ModelsConfig)
        assert isinstance(config.generation_params, GenerationParamsConfig)
        assert isinstance(config.rag, RAGConfig)
        assert isinstance(config.output_contract, OutputContractConfig)
        assert isinstance(config.telemetry, TelemetryConfig)
        assert isinstance(config.policy, PolicyConfig)
        assert config.tools_allowlist == []

    def test_use_case_config_from_dict(self):
        """Test creating UseCaseConfig from dictionary (ADR-023: with sampling preset)."""
        data = {
            "visibility": {"roles": ["analyst"], "tags": ["test"]},
            "models": {"llm": "gpt-4-turbo"},
            "generation_params": {
                "sampling_preset": "custom",
                "temperature": 0.5,
                "max_tokens": 2048,
                "top_p": 0.9,
            },
            "rag": {"enabled": True, "top_k": 5},
            "output_contract": {"format": "json"},
            "telemetry": {"required_metrics": ["retrieval"]},
            "policy": {"streaming_enabled": False},
            "tools_allowlist": ["web_search"],
        }
        config = UseCaseConfig.from_dict(data)
        assert config.visibility.roles == ["analyst"]
        assert config.models.llm == "gpt-4-turbo"
        assert config.generation_params.sampling_preset == SamplingPreset.CUSTOM
        assert config.generation_params.temperature == 0.5
        assert config.rag.top_k == 5
        assert config.output_contract.format == OutputFormat.JSON
        assert config.telemetry.required_metrics == ["retrieval"]
        assert config.policy.streaming_enabled is False
        assert config.tools_allowlist == ["web_search"]

    def test_use_case_config_to_dict(self):
        """Test converting UseCaseConfig to dictionary."""
        config = UseCaseConfig()
        data = config.to_dict()
        assert isinstance(data, dict)
        assert "visibility" in data
        assert "models" in data
        assert "generation_params" in data
        assert "rag" in data
        assert "output_contract" in data
        assert "telemetry" in data
        assert "policy" in data
        assert "tools_allowlist" in data

    def test_use_case_config_merge(self):
        """Test merging UseCaseConfig instances (ADR-023: with presets)."""
        base_config = UseCaseConfig()
        override_config = UseCaseConfig(
            models=ModelsConfig(llm="gpt-4-turbo"),
            generation_params=GenerationParamsConfig(sampling_preset=SamplingPreset.STRICT),
        )

        merged = base_config.merge_with(override_config)
        assert merged.models.llm == "gpt-4-turbo"
        assert merged.generation_params.sampling_preset == SamplingPreset.STRICT
        # Other fields should remain from base
        assert merged.rag.enabled is True
        assert merged.policy.streaming_enabled is True

    def test_tools_allowlist_validation(self):
        """Test tools_allowlist validation."""
        # Valid tools_allowlist
        config = UseCaseConfig(tools_allowlist=["web_search", "tanium_query"])
        assert config.tools_allowlist == ["web_search", "tanium_query"]

        # Empty tools_allowlist is valid
        config = UseCaseConfig(tools_allowlist=[])
        assert config.tools_allowlist == []

        # Invalid tools_allowlist raises error
        with pytest.raises(ValidationError) as exc_info:
            UseCaseConfig(tools_allowlist=["", "valid_tool"])
        assert "All tools in allowlist must be non-empty strings" in str(exc_info.value)

    def test_rag_config_validation(self):
        """Test RAG configuration validation."""
        # Valid RAG config
        config = UseCaseConfig(rag=RAGConfig(enabled=True, vector_collections=["docs"], top_k=5))
        assert config.rag.enabled is True
        assert config.rag.vector_collections == ["docs"]
        assert config.rag.top_k == 5

        # RAG disabled with empty collections is valid (not enforced when disabled)
        config = UseCaseConfig(rag=RAGConfig(enabled=False, vector_collections=[], top_k=5))
        assert config.rag.enabled is False

        # top_k must be positive (enforced by Field constraint)
        with pytest.raises(ValidationError) as exc_info:
            RAGConfig(enabled=True, vector_collections=["docs"], top_k=-1)
        assert "Input should be greater than 0" in str(exc_info.value)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            UseCaseConfig(extra_field="not_allowed")
        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_get_default_config(self):
        """Test getting default configuration."""
        config = UseCaseConfig.get_default_config()
        assert isinstance(config, UseCaseConfig)
        assert config.models.llm == "foundation-sec-8b-instruct-mlx"
        assert config.rag.enabled is True


class TestUseCaseConfigIntegration:
    """Integration tests for UseCaseConfig with real-world scenarios."""

    def test_threat_hunting_config(self):
        """Test threat hunting use case configuration (ADR-023: with balanced preset)."""
        config = UseCaseConfig(
            visibility=VisibilityConfig(
                roles=["analyst", "senior_analyst"],
                tags=["threat_hunting", "investigation"],
            ),
            models=ModelsConfig(llm="gpt-4o"),
            generation_params=GenerationParamsConfig(sampling_preset=SamplingPreset.BALANCED),
            rag=RAGConfig(
                enabled=True,
                vector_collections=["documents", "threat_intel"],
                top_k=10,
                similarity_threshold=0.6,
                metadata_filters={"classification": "threat-intelligence"},
                tags=["malware", "apt"],
            ),
            tools_allowlist=["web_search", "tanium_signal_query"],
            output_contract=OutputContractConfig(format=OutputFormat.TEXT),
            telemetry=TelemetryConfig(
                required_metrics=["retrieval", "guard", "performance", "model"]
            ),
            policy=PolicyConfig(
                streaming_enabled=True,
                streaming_default=False,
                history_persistence=True,
                pii_redaction=PIIRedactionMode.ANONYMIZE,
            ),
        )

        # Verify all fields are set correctly
        assert config.visibility.roles == ["analyst", "senior_analyst"]
        assert config.models.llm == "gpt-4o"
        assert config.rag.vector_collections == ["documents", "threat_intel"]
        assert config.tools_allowlist == ["web_search", "tanium_signal_query"]
        assert config.output_contract.format == OutputFormat.TEXT
        assert config.policy.pii_redaction == PIIRedactionMode.ANONYMIZE

    def test_rule_generation_config(self):
        """Test rule generation use case configuration (ADR-023: deterministic preset)."""
        config = UseCaseConfig(
            visibility=VisibilityConfig(
                roles=["analyst", "senior_analyst"],
                tags=["rule_generation", "detection"],
            ),
            models=ModelsConfig(llm="gpt-4o"),
            generation_params=GenerationParamsConfig(sampling_preset=SamplingPreset.STRICT),
            rag=RAGConfig(
                enabled=True,
                vector_collections=["documents", "rule_examples"],
                top_k=5,
                similarity_threshold=0.7,
                hybrid_bm25=True,
                metadata_filters={"classification": "rule-examples"},
                tags=["yara", "kql", "tanium"],
            ),
            tools_allowlist=["web_search"],
            output_contract=OutputContractConfig(
                format=OutputFormat.JSON,
                output_schema={
                    "type": "object",
                    "required": ["rule_name", "rule_content"],
                    "properties": {
                        "rule_name": {"type": "string"},
                        "rule_content": {"type": "string"},
                    },
                },
                validation_mode=ValidationMode.STRICT,
            ),
            telemetry=TelemetryConfig(
                required_metrics=["retrieval", "guard", "performance", "model"]
            ),
            policy=PolicyConfig(
                streaming_enabled=True,
                streaming_default=False,
                history_persistence=True,
                pii_redaction=PIIRedactionMode.ANONYMIZE,
            ),
        )

        # Verify all fields are set correctly
        assert config.generation_params.sampling_preset == SamplingPreset.STRICT
        assert config.rag.hybrid_bm25 is True
        assert config.output_contract.format == OutputFormat.JSON
        assert config.output_contract.validation_mode == ValidationMode.STRICT
        assert config.output_contract.output_schema is not None

    def test_user_prompt_template_optional(self):
        """Test UseCaseConfig with optional user_prompt_template (Phase 2)."""
        config = UseCaseConfig(
            user_prompt_template=UserPromptTemplateConfig(
                template="Analyze {{incident_id}} with {{severity}}.",
                variables=["incident_id", "severity"],
                fallback_mode="concatenate",
            ),
        )
        assert config.user_prompt_template is not None
        assert "incident_id" in config.user_prompt_template.template
        assert config.user_prompt_template.fallback_mode == "concatenate"

    def test_user_prompt_template_default_none(self):
        """Test UseCaseConfig defaults user_prompt_template to None."""
        config = UseCaseConfig()
        assert config.user_prompt_template is None
