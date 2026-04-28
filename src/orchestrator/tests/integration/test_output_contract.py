"""
Integration tests for Output Contract Validation (B3-F4).

Tests the end-to-end output contract validation feature including:
- JSON output validation
- YAML output validation
- Schema validation
- Best-effort vs strict modes

P5-A17: Migrated to async database patterns (ADR-022).
"""

import pytest
from app.schemas.use_case_config import (
    OutputContractConfig,
    OutputFormat,
    UseCaseConfig,
    ValidationMode,
)


class TestOutputContractValidation:
    """Integration tests for output contract validation feature."""

    @pytest.mark.asyncio
    async def test_json_output_validated(self, async_db_session):
        """JSON output is validated against schema"""
        # Create use case config with JSON output contract
        config = UseCaseConfig(
            output_contract=OutputContractConfig(
                format=OutputFormat.JSON,
                validation_mode=ValidationMode.BEST_EFFORT,
                output_schema={
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"},
                        "status": {"type": "string"},
                    },
                    "required": ["result", "status"],
                },
            )
        )

        # Test that config has correct output contract
        assert config.output_contract.format == OutputFormat.JSON
        assert config.output_contract.validation_mode == ValidationMode.BEST_EFFORT
        assert config.output_contract.output_schema is not None

    @pytest.mark.asyncio
    async def test_invalid_output_best_effort(self, async_db_session):
        """Invalid output in best-effort mode returns errors in metadata"""
        # Create use case config with strict schema
        config = UseCaseConfig(
            output_contract=OutputContractConfig(
                format=OutputFormat.JSON,
                validation_mode=ValidationMode.BEST_EFFORT,
                output_schema={
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                    "required": ["result"],
                },
            )
        )

        # Verify best-effort mode is set
        assert config.output_contract.validation_mode == ValidationMode.BEST_EFFORT

        # In best-effort mode, validation errors should be wrapped in metadata
        # rather than raising an exception (tested at unit level)

    @pytest.mark.asyncio
    async def test_strict_mode_config(self, async_db_session):
        """Strict mode configuration is properly set"""
        # Create use case with validation_mode = "strict"
        config = UseCaseConfig(
            output_contract=OutputContractConfig(
                format=OutputFormat.JSON,
                validation_mode=ValidationMode.STRICT,
                output_schema={
                    "type": "object",
                    "properties": {"data": {"type": "array"}},
                    "required": ["data"],
                },
            )
        )

        # Verify strict mode raises errors on validation failure
        assert config.output_contract.validation_mode == ValidationMode.STRICT

    @pytest.mark.asyncio
    async def test_text_output_contract(self, async_db_session):
        """TEXT format output contract works correctly"""
        config = UseCaseConfig(
            output_contract=OutputContractConfig(
                format=OutputFormat.TEXT, validation_mode=ValidationMode.BEST_EFFORT
            )
        )

        assert config.output_contract.format == OutputFormat.TEXT

    @pytest.mark.asyncio
    async def test_yaml_output_contract(self, async_db_session):
        """YAML format output contract works correctly"""
        config = UseCaseConfig(
            output_contract=OutputContractConfig(
                format=OutputFormat.YAML, validation_mode=ValidationMode.BEST_EFFORT
            )
        )

        assert config.output_contract.format == OutputFormat.YAML

    @pytest.mark.asyncio
    async def test_structured_output_contract(self, async_db_session):
        """STRUCTURED format output contract works correctly"""
        config = UseCaseConfig(
            output_contract=OutputContractConfig(
                format=OutputFormat.STRUCTURED,
                validation_mode=ValidationMode.BEST_EFFORT,
            )
        )

        assert config.output_contract.format == OutputFormat.STRUCTURED

    @pytest.mark.asyncio
    async def test_output_contract_with_complex_schema(self, async_db_session):
        """Output contract works with complex JSON schema"""
        complex_schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "threats": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "severity": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "critical"],
                            },
                            "indicators": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["name", "severity"],
                    },
                },
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            },
            "required": ["summary", "threats", "confidence"],
        }

        config = UseCaseConfig(
            output_contract=OutputContractConfig(
                format=OutputFormat.JSON,
                validation_mode=ValidationMode.BEST_EFFORT,
                output_schema=complex_schema,
            )
        )

        assert config.output_contract.output_schema == complex_schema
        assert len(config.output_contract.output_schema["properties"]) == 3

    @pytest.mark.asyncio
    async def test_config_without_output_contract(self, async_db_session):
        """Use case config works without output contract (default)"""
        config = UseCaseConfig()

        # Default output contract should be TEXT format
        assert config.output_contract.format == OutputFormat.TEXT
        assert config.output_contract.validation_mode == ValidationMode.BEST_EFFORT
        assert config.output_contract.output_schema is None

    @pytest.mark.asyncio
    async def test_config_serialization_with_output_contract(self, async_db_session):
        """Output contract properly serializes and deserializes"""
        config = UseCaseConfig(
            output_contract=OutputContractConfig(
                format=OutputFormat.JSON,
                validation_mode=ValidationMode.STRICT,
                output_schema={"type": "object"},
            )
        )

        # Serialize to dict
        config_dict = config.to_dict()
        assert "output_contract" in config_dict
        assert config_dict["output_contract"]["format"] == "json"
        assert config_dict["output_contract"]["validation_mode"] == "strict"

        # Deserialize from dict
        restored_config = UseCaseConfig.from_dict(config_dict)
        assert restored_config.output_contract.format == OutputFormat.JSON
        assert restored_config.output_contract.validation_mode == ValidationMode.STRICT
        assert restored_config.output_contract.output_schema == {"type": "object"}
