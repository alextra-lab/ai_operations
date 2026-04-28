"""
Integration tests for UseCaseConfig with database.

Tests UseCaseConfig schema integration with PostgreSQL database,
including JSONB serialization/deserialization and constraint validation.

P5-A17: Migrated to async database patterns (ADR-022).
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.orchestrator.app.db.models import UseCase
from src.orchestrator.app.schemas.use_case_config import (
    OutputFormat,
    UseCaseConfig,
    ValidationMode,
)


class TestUseCaseConfigDatabaseIntegration:
    """Test UseCaseConfig integration with database."""

    @pytest.mark.asyncio
    async def test_use_case_config_serialization(self, async_db_session: AsyncSession):
        """Test serializing UseCaseConfig to JSONB."""
        config = UseCaseConfig()
        config_dict = config.to_dict()

        # Create use case with config
        use_case = UseCase(
            use_case_id="test_config_serialization",  # type: ignore
            name="Test Config Serialization",  # type: ignore
            description="Test use case for config serialization",  # type: ignore
            category="test",  # type: ignore
            intent_type="QUERY",  # type: ignore
            is_active=True,  # type: ignore
            config_json=config_dict,  # type: ignore
            created_by_user_id=None,  # Allow NULL for test  # type: ignore
        )

        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        # Verify config was stored correctly
        assert use_case.config_json is not None
        assert isinstance(use_case.config_json, dict)
        assert "visibility" in use_case.config_json
        assert "models" in use_case.config_json
        assert "rag" in use_case.config_json

    @pytest.mark.asyncio
    async def test_use_case_config_deserialization(self, async_db_session: AsyncSession):
        """Test deserializing UseCaseConfig from JSONB."""
        # Create a complex config
        config = UseCaseConfig(
            visibility={"roles": ["analyst"], "tags": ["test"]},  # type: ignore
            models={"llm": "gpt-4-turbo", "embedding": "text-embedding-3-large"},  # type: ignore
            generation_params={"temperature": 0.5, "max_tokens": 2048},  # type: ignore
            rag={"enabled": True, "top_k": 5, "vector_collections": ["docs"]},  # type: ignore
            output_contract={"format": "json", "validation_mode": "strict"},  # type: ignore
            telemetry={"required_metrics": ["retrieval", "performance"]},  # type: ignore
            policy={"streaming_enabled": False, "pii_redaction": "redact"},  # type: ignore
            tools_allowlist=["web_search", "tanium_query"],
        )

        # Store in database
        use_case = UseCase(
            use_case_id="test_config_deserialization",  # type: ignore
            name="Test Config Deserialization",  # type: ignore
            description="Test use case for config deserialization",  # type: ignore
            category="test",  # type: ignore
            intent_type="QUERY",  # type: ignore
            is_active=True,  # type: ignore
            config_json=config.to_dict(),  # type: ignore
            created_by_user_id=None,  # type: ignore
        )

        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        # Deserialize from database
        loaded_config = UseCaseConfig.from_dict(use_case.config_json)

        # Verify all fields match
        assert loaded_config.visibility.roles == ["analyst"]
        assert loaded_config.models.llm == "gpt-4-turbo"
        assert loaded_config.generation_params.temperature == 0.5
        assert loaded_config.rag.top_k == 5
        assert loaded_config.output_contract.format == OutputFormat.JSON
        assert loaded_config.output_contract.validation_mode == ValidationMode.STRICT
        assert loaded_config.tools_allowlist == ["web_search", "tanium_query"]

    @pytest.mark.asyncio
    async def test_use_case_config_validation_constraints(self, async_db_session: AsyncSession):
        """Test database constraint validation for UseCaseConfig."""
        # Test empty config_json constraint
        with pytest.raises(IntegrityError) as exc_info:
            use_case = UseCase(
                use_case_id="test_empty_config",  # type: ignore
                name="Test Empty Config",  # type: ignore
                description="Test use case with empty config",  # type: ignore
                category="test",  # type: ignore
                intent_type="QUERY",  # type: ignore
                is_active=True,  # type: ignore
                config_json={},  # Empty config should fail  # type: ignore
                created_by_user_id=None,  # type: ignore
            )
            async_db_session.add(use_case)
            await async_db_session.commit()
        assert "use_cases_config_json_not_empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_use_case_config_missing_required_fields(self, async_db_session: AsyncSession):
        """Test database constraint for missing required fields."""
        # Test missing required fields
        incomplete_config = {
            "visibility": {"roles": ["analyst"]},
            "models": {"llm": "gpt-4o"},
            # Missing other required fields
        }

        with pytest.raises(IntegrityError) as exc_info:
            use_case = UseCase(
                use_case_id="test_incomplete_config",  # type: ignore
                name="Test Incomplete Config",  # type: ignore
                description="Test use case with incomplete config",  # type: ignore
                category="test",  # type: ignore
                intent_type="QUERY",  # type: ignore
                is_active=True,  # type: ignore
                config_json=incomplete_config,  # type: ignore
                created_by_user_id=None,  # type: ignore
            )
            async_db_session.add(use_case)
            await async_db_session.commit()
        assert "use_cases_config_json_structure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_use_case_config_invalid_llm(self, async_db_session: AsyncSession):
        """Test database constraint for invalid LLM."""
        config = UseCaseConfig()
        config_dict = config.to_dict()
        config_dict["models"]["llm"] = ""  # Empty LLM should fail

        with pytest.raises(IntegrityError) as exc_info:
            use_case = UseCase(
                use_case_id="test_invalid_llm",  # type: ignore
                name="Test Invalid LLM",  # type: ignore
                description="Test use case with invalid LLM",  # type: ignore
                category="test",  # type: ignore
                intent_type="QUERY",  # type: ignore
                is_active=True,  # type: ignore
                config_json=config_dict,  # type: ignore
                created_by_user_id=None,  # type: ignore
            )
            async_db_session.add(use_case)
            await async_db_session.commit()
        assert "use_cases_config_models_llm_not_empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_use_case_config_invalid_temperature(self, async_db_session: AsyncSession):
        """Test database constraint for invalid temperature."""
        config = UseCaseConfig()
        config_dict = config.to_dict()
        config_dict["generation_params"]["sampling_preset"] = "custom"
        config_dict["generation_params"]["temperature"] = 1.5  # Out of range

        with pytest.raises(IntegrityError) as exc_info:
            use_case = UseCase(
                use_case_id="test_invalid_temperature",  # type: ignore
                name="Test Invalid Temperature",  # type: ignore
                description="Test use case with invalid temperature",  # type: ignore
                category="test",  # type: ignore
                intent_type="QUERY",  # type: ignore
                is_active=True,  # type: ignore
                config_json=config_dict,  # type: ignore
                created_by_user_id=None,  # type: ignore
            )
            async_db_session.add(use_case)
            await async_db_session.commit()
        assert "use_cases_config_temperature_range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_use_case_config_invalid_top_k(self, async_db_session: AsyncSession):
        """Test database constraint for invalid top_k."""
        config = UseCaseConfig()
        config_dict = config.to_dict()
        config_dict["rag"]["top_k"] = 0  # Invalid top_k

        with pytest.raises(IntegrityError) as exc_info:
            use_case = UseCase(
                use_case_id="test_invalid_top_k",  # type: ignore
                name="Test Invalid Top K",  # type: ignore
                description="Test use case with invalid top_k",  # type: ignore
                category="test",  # type: ignore
                intent_type="QUERY",  # type: ignore
                is_active=True,  # type: ignore
                config_json=config_dict,  # type: ignore
                created_by_user_id=None,  # type: ignore
            )
            async_db_session.add(use_case)
            await async_db_session.commit()
        assert "use_cases_config_rag_top_k_positive" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_use_case_config_invalid_output_format(self, async_db_session: AsyncSession):
        """Test database constraint for invalid output format."""
        config = UseCaseConfig()
        config_dict = config.to_dict()
        config_dict["output_contract"]["format"] = "invalid_format"

        with pytest.raises(IntegrityError) as exc_info:
            use_case = UseCase(
                use_case_id="test_invalid_output_format",  # type: ignore
                name="Test Invalid Output Format",  # type: ignore
                description="Test use case with invalid output format",  # type: ignore
                category="test",  # type: ignore
                intent_type="QUERY",  # type: ignore
                is_active=True,  # type: ignore
                config_json=config_dict,  # type: ignore
                created_by_user_id=None,  # type: ignore
            )
            async_db_session.add(use_case)
            await async_db_session.commit()
        assert "use_cases_config_output_format_valid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_use_case_config_invalid_pii_redaction(self, async_db_session: AsyncSession):
        """Test database constraint for invalid PII redaction mode."""
        config = UseCaseConfig()
        config_dict = config.to_dict()
        config_dict["policy"]["pii_redaction"] = "invalid_mode"

        with pytest.raises(IntegrityError) as exc_info:
            use_case = UseCase(
                use_case_id="test_invalid_pii_redaction",  # type: ignore
                name="Test Invalid PII Redaction",  # type: ignore
                description="Test use case with invalid PII redaction",  # type: ignore
                category="test",  # type: ignore
                intent_type="QUERY",  # type: ignore
                is_active=True,  # type: ignore
                config_json=config_dict,  # type: ignore
                created_by_user_id=None,  # type: ignore
            )
            async_db_session.add(use_case)
            await async_db_session.commit()
        assert "use_cases_config_pii_redaction_valid" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_use_case_config_valid_complex_config(self, async_db_session: AsyncSession):
        """Test storing and retrieving a complex, valid configuration."""
        config = UseCaseConfig(
            visibility={"roles": ["analyst", "admin"], "tags": ["threat_hunting"]},  # type: ignore
            models={"llm": "gpt-4o", "embedding": "text-embedding-3-small"},  # type: ignore
            generation_params={  # type: ignore
                "temperature": 0.7,
                "max_tokens": 1024,
                "top_p": 0.95,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
            },
            rag={  # type: ignore
                "enabled": True,
                "vector_collections": ["documents", "threat_intel"],
                "top_k": 10,
                "similarity_threshold": 0.6,
                "hybrid_bm25": False,
                "metadata_filters": {"classification": "threat-intelligence"},
                "tags": ["malware", "apt"],
            },
            tools_allowlist=["web_search", "tanium_signal_query"],
            output_contract={  # type: ignore
                "format": "json",
                "schema": {
                    "type": "object",
                    "required": ["rule_name", "rule_content"],
                    "properties": {
                        "rule_name": {"type": "string"},
                        "rule_content": {"type": "string"},
                    },
                },
                "validation_mode": "strict",
            },
            telemetry={  # type: ignore
                "required_metrics": ["retrieval", "guard", "performance", "model"]
            },
            policy={  # type: ignore
                "streaming_enabled": True,
                "streaming_default": False,
                "history_persistence": True,
                "pii_redaction": "anonymize",
            },
        )

        # Store in database
        use_case = UseCase(
            use_case_id="test_complex_config",  # type: ignore
            name="Test Complex Config",  # type: ignore
            description="Test use case with complex configuration",  # type: ignore
            category="threat_hunting",  # type: ignore
            intent_type="QUERY",  # type: ignore
            is_active=True,  # type: ignore
            config_json=config.to_dict(),  # type: ignore
            created_by_user_id=None,  # type: ignore
        )

        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        # Verify storage
        assert use_case.config_json is not None
        assert use_case.config_json["models"]["llm"] == "gpt-4o"
        assert use_case.config_json["rag"]["top_k"] == 10
        assert use_case.config_json["output_contract"]["format"] == "json"

        # Verify deserialization
        loaded_config = UseCaseConfig.from_dict(use_case.config_json)
        assert loaded_config.visibility.roles == ["analyst", "admin"]
        assert loaded_config.models.llm == "gpt-4o"
        assert loaded_config.rag.vector_collections == ["documents", "threat_intel"]
        assert loaded_config.tools_allowlist == ["web_search", "tanium_signal_query"]
        assert loaded_config.output_contract.format == OutputFormat.JSON
        assert loaded_config.policy.pii_redaction == "anonymize"

    @pytest.mark.asyncio
    async def test_use_case_config_merge_functionality(self, async_db_session: AsyncSession):
        """Test config merging functionality with database."""
        base_config = UseCaseConfig()
        override_config = UseCaseConfig(
            models={"llm": "gpt-4-turbo"},  # type: ignore
            generation_params={"temperature": 0.5},  # type: ignore
            rag={"top_k": 5},  # type: ignore
        )

        merged_config = base_config.merge_with(override_config)

        # Store merged config
        use_case = UseCase(
            use_case_id="test_merged_config",  # type: ignore
            name="Test Merged Config",  # type: ignore
            description="Test use case with merged configuration",  # type: ignore
            category="test",  # type: ignore
            intent_type="QUERY",  # type: ignore
            is_active=True,  # type: ignore
            config_json=merged_config.to_dict(),  # type: ignore
            created_by_user_id=None,  # type: ignore
        )

        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        # Verify merged config
        loaded_config = UseCaseConfig.from_dict(use_case.config_json)
        assert loaded_config.models.llm == "gpt-4-turbo"
        assert loaded_config.generation_params.temperature == 0.5
        assert loaded_config.rag.top_k == 5
        # Other fields should be from base config
        assert loaded_config.rag.enabled is True
        assert loaded_config.policy.streaming_enabled is True
