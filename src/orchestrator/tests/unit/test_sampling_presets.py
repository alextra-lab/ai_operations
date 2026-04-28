"""
Unit tests for Sampling Presets functionality (ADR-023).

Tests cover:
- Preset resolution to explicit parameters
- High-entropy detection
- Custom preset validation
- Backward compatibility
"""

import pytest
from app.schemas.use_case_config import (
    GenerationParamsConfig,
    SamplingPreset,
)
from pydantic import ValidationError


class TestSamplingPresets:
    """Test suite for sampling preset functionality."""

    def test_default_preset_is_balanced(self):
        """Test that default preset is 'balanced'."""
        config = GenerationParamsConfig()
        assert config.sampling_preset == SamplingPreset.BALANCED

    def test_deterministic_preset_resolution(self):
        """Test deterministic preset resolves to correct parameters."""
        config = GenerationParamsConfig(sampling_preset=SamplingPreset.STRICT)
        params = config.get_effective_params()

        assert params["temperature"] == 0.15
        assert params["top_p"] == 0.90
        assert params["max_tokens"] == 1024

    def test_balanced_preset_resolution(self):
        """Test balanced preset resolves to correct parameters."""
        config = GenerationParamsConfig(sampling_preset=SamplingPreset.BALANCED)
        params = config.get_effective_params()

        assert params["temperature"] == 0.65
        assert params["top_p"] == 0.95
        assert params["max_tokens"] == 2048

    def test_creative_preset_resolution(self):
        """Test creative preset resolves to correct parameters."""
        config = GenerationParamsConfig(sampling_preset=SamplingPreset.CREATIVE)
        params = config.get_effective_params()

        assert params["temperature"] == 0.85
        assert params["top_p"] == 0.97
        assert params["max_tokens"] == 4096

    def test_custom_preset_with_overrides(self):
        """Test custom preset with explicit parameter overrides."""
        config = GenerationParamsConfig(
            sampling_preset=SamplingPreset.CUSTOM,
            temperature=0.5,
            max_tokens=1500,
            top_p=0.92,
        )
        params = config.get_effective_params()

        assert params["temperature"] == 0.5
        assert params["top_p"] == 0.92
        assert params["max_tokens"] == 1500

    def test_custom_preset_fallback_defaults(self):
        """Test custom preset uses fallback defaults when no overrides provided."""
        config = GenerationParamsConfig(sampling_preset=SamplingPreset.CUSTOM)
        params = config.get_effective_params()

        # Custom preset with no overrides should use fallback defaults
        assert params["temperature"] == 0.7
        assert params["top_p"] == 0.95
        assert params["max_tokens"] == 2048

    def test_preset_includes_penalties(self):
        """Test that effective params include penalty parameters."""
        config = GenerationParamsConfig(
            sampling_preset=SamplingPreset.BALANCED,
            frequency_penalty=0.5,
            presence_penalty=0.3,
        )
        params = config.get_effective_params()

        assert params["frequency_penalty"] == 0.5
        assert params["presence_penalty"] == 0.3

    def test_override_requires_custom_preset_temperature(self):
        """Test that temperature override requires CUSTOM preset."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationParamsConfig(sampling_preset=SamplingPreset.BALANCED, temperature=0.9)

        assert "requires sampling_preset='custom'" in str(exc_info.value)

    def test_override_requires_custom_preset_top_p(self):
        """Test that top_p override requires CUSTOM preset."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationParamsConfig(sampling_preset=SamplingPreset.STRICT, top_p=0.99)

        assert "requires sampling_preset='custom'" in str(exc_info.value)

    def test_null_parameters_allowed_for_non_custom_presets(self):
        """Test that null parameters are allowed for non-custom presets."""
        config = GenerationParamsConfig(
            sampling_preset=SamplingPreset.BALANCED,
            temperature=None,
            max_tokens=None,
            top_p=None,
        )

        # Should not raise ValidationError
        assert config.sampling_preset == SamplingPreset.BALANCED

    def test_high_entropy_detection_warning(self, caplog):
        """Test high-entropy configuration warning."""
        import logging

        caplog.set_level(logging.WARNING)

        config = GenerationParamsConfig(
            sampling_preset=SamplingPreset.CUSTOM, temperature=0.95, top_p=0.99
        )

        _ = config.get_effective_params()

        # Check for warning in logs
        assert any("high-entropy" in record.message.lower() for record in caplog.records)

    def test_no_warning_for_safe_custom_params(self, caplog):
        """Test no warning for safe custom parameters."""
        import logging

        caplog.set_level(logging.WARNING)

        config = GenerationParamsConfig(
            sampling_preset=SamplingPreset.CUSTOM, temperature=0.7, top_p=0.95
        )

        _ = config.get_effective_params()

        # Should not generate warning
        assert not any("high-entropy" in record.message.lower() for record in caplog.records)

    def test_no_warning_for_non_custom_presets(self, caplog):
        """Test no warning for non-custom presets even with high values."""
        import logging

        caplog.set_level(logging.WARNING)

        # Creative preset has high values but should not trigger warning
        config = GenerationParamsConfig(sampling_preset=SamplingPreset.CREATIVE)
        _ = config.get_effective_params()

        assert not any("high-entropy" in record.message.lower() for record in caplog.records)

    def test_tool_specific_params_included(self):
        """Test that tool-specific parameters are included in effective params."""
        config = GenerationParamsConfig(
            sampling_preset=SamplingPreset.BALANCED,
            max_tool_steps=5,
            tool_step_timeout=45,
        )

        params = config.get_effective_params()

        assert params["max_tool_steps"] == 5
        assert params["tool_step_timeout"] == 45

    def test_tool_params_optional(self):
        """Test that tool-specific parameters are optional."""
        config = GenerationParamsConfig(sampling_preset=SamplingPreset.BALANCED)

        params = config.get_effective_params()

        # max_tool_steps should not be in params when not set
        assert "max_tool_steps" not in params
        # tool_step_timeout has default value
        assert params["tool_step_timeout"] == 30

    def test_parameter_bounds_validation(self):
        """Test that parameter bounds are enforced."""
        # Temperature out of bounds
        with pytest.raises(ValidationError):
            GenerationParamsConfig(sampling_preset=SamplingPreset.CUSTOM, temperature=3.0)

        # Top-p out of bounds
        with pytest.raises(ValidationError):
            GenerationParamsConfig(sampling_preset=SamplingPreset.CUSTOM, top_p=1.5)

        # Max tokens out of bounds
        with pytest.raises(ValidationError):
            GenerationParamsConfig(sampling_preset=SamplingPreset.CUSTOM, max_tokens=20000)

    def test_preset_serialization(self):
        """Test that presets serialize correctly to dict."""
        config = GenerationParamsConfig(sampling_preset=SamplingPreset.STRICT)

        config_dict = config.model_dump()

        assert config_dict["sampling_preset"] == "strict"
        assert config_dict["temperature"] is None
        assert config_dict["max_tokens"] is None
        assert config_dict["top_p"] is None

    def test_preset_deserialization(self):
        """Test that presets deserialize correctly from dict."""
        config_dict = {
            "sampling_preset": "creative",
            "temperature": None,
            "max_tokens": None,
            "top_p": None,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
        }

        config = GenerationParamsConfig(**config_dict)

        assert config.sampling_preset == SamplingPreset.CREATIVE
        params = config.get_effective_params()
        assert params["temperature"] == 0.85
        assert params["max_tokens"] == 4096

    def test_backward_compatibility_with_explicit_params(self):
        """Test backward compatibility: old configs with explicit params should migrate to CUSTOM."""
        # Simulate old config that had explicit parameters
        config = GenerationParamsConfig(
            sampling_preset=SamplingPreset.CUSTOM,  # Would be set during migration
            temperature=0.7,
            max_tokens=2048,
            top_p=0.95,
        )

        params = config.get_effective_params()

        # Should preserve the explicit values
        assert params["temperature"] == 0.7
        assert params["max_tokens"] == 2048
        assert params["top_p"] == 0.95
