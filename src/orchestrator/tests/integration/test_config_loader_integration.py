"""
Integration tests for UseCaseConfigLoader service.

Tests the configuration loader with real database interactions,
including database setup, data persistence, and error handling.

P5-A17: Migrated to async database patterns (ADR-022).
"""

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from src.orchestrator.app.db.models import UseCase
from src.orchestrator.app.schemas.intent import RequestType
from src.orchestrator.app.schemas.use_case_config import UseCaseConfig
from src.orchestrator.app.services.use_case_config_loader import UseCaseConfigLoader


class TestConfigLoaderIntegration:
    """Integration tests for UseCaseConfigLoader with real database."""

    @pytest_asyncio.fixture
    async def config_loader(self, async_db_session):
        """Create a UseCaseConfigLoader with real async database session."""
        return UseCaseConfigLoader(async_db_session)

    @pytest.fixture
    def sample_use_case_data(self):
        """Create sample use case data for testing."""
        return {
            "use_case_id": "integration_test_use_case",
            "name": "Integration Test Use Case",
            "description": "Test use case for integration testing",
            "category": "test",
            "intent_type": "QUERY",
            "is_active": True,
            "config_json": {
                "visibility": {
                    "roles": ["analyst", "admin"],
                    "tags": ["integration_test"],
                },
                "models": {"llm": "gpt-4o", "embedding": "text-embedding-3-small"},
                "generation_params": {
                    "sampling_preset": "custom",
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
                "rag": {
                    "enabled": True,
                    "top_k": 10,
                    "vector_collections": ["documents"],
                },
                "output_contract": {"format": "text"},
                "telemetry": {"required_metrics": ["retrieval", "performance"]},
                "policy": {"streaming_enabled": True, "streaming_default": False},
                "tools_allowlist": ["web_search"],
            },
            "created_by_user_id": None,
        }

    @pytest.fixture
    def sample_use_case_2_data(self):
        """Create second sample use case data for testing."""
        return {
            "use_case_id": "integration_test_use_case_2",
            "name": "Integration Test Use Case 2",
            "description": "Second test use case for integration testing",
            "category": "test",
            "intent_type": "SUMMARIZATION",
            "is_active": True,
            "config_json": {
                "visibility": {"roles": ["analyst"], "tags": ["summarization"]},
                "models": {"llm": "gpt-4-turbo", "embedding": "text-embedding-3-large"},
                "generation_params": {
                    "sampling_preset": "custom",
                    "temperature": 0.3,
                    "max_tokens": 2048,
                },
                "rag": {
                    "enabled": True,
                    "top_k": 5,
                    "vector_collections": ["documents", "summaries"],
                },
                "output_contract": {"format": "json"},
                "telemetry": {"required_metrics": ["retrieval", "model", "confidence"]},
                "policy": {"streaming_enabled": True, "streaming_default": True},
                "tools_allowlist": [],
            },
            "created_by_user_id": None,
        }

    @pytest.mark.asyncio
    async def test_load_config_from_database(
        self, config_loader, async_db_session, sample_use_case_data
    ):
        """Test loading config from real database."""
        # Create use case in database
        use_case = UseCase(**sample_use_case_data)
        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        try:
            # Load config by UUID (id field)
            config = await config_loader.load_config(str(use_case.id))

            # Verify config was loaded correctly
            assert config is not None
            assert isinstance(config, UseCaseConfig)
            assert config.models.llm == "gpt-4o"
            assert config.rag.top_k == 10
            assert config.generation_params.temperature == 0.7
            assert config.policy.streaming_enabled is True
            assert config.tools_allowlist == ["web_search"]

        finally:
            # Cleanup
            await async_db_session.execute(delete(UseCase).where(UseCase.id == use_case.id))
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_load_config_by_intent_from_database(
        self, config_loader, async_db_session, sample_use_case_data
    ):
        """Test loading config by intent from real database."""
        # Create use case in database
        use_case = UseCase(**sample_use_case_data)
        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        try:
            # Load config by intent
            config = await config_loader.load_config_by_intent(RequestType.QUERY)

            # Verify config was loaded correctly
            assert config is not None
            assert isinstance(config, UseCaseConfig)
            assert config.models.llm == "gpt-4o"
            assert config.rag.top_k == 10
            assert config.generation_params.temperature == 0.7
            assert config.policy.streaming_enabled is True

        finally:
            # Cleanup
            await async_db_session.execute(delete(UseCase).where(UseCase.id == use_case.id))
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_load_config_not_found(self, config_loader):
        """Test loading config when use case doesn't exist."""
        from uuid import uuid4

        # Use a valid UUID format that doesn't exist
        nonexistent_uuid = str(uuid4())
        config = await config_loader.load_config(nonexistent_uuid)
        assert config is None

    @pytest.mark.asyncio
    async def test_load_config_by_intent_not_found(self, config_loader):
        """Test loading config by intent when no use case exists."""
        config = await config_loader.load_config_by_intent(RequestType.RULE_GENERATION)
        assert config is None

    @pytest.mark.asyncio
    async def test_load_config_inactive_use_case(
        self, config_loader, async_db_session, sample_use_case_data
    ):
        """Test loading config from inactive use case."""
        # Create inactive use case
        use_case_data = sample_use_case_data.copy()
        use_case_data["is_active"] = False
        use_case = UseCase(**use_case_data)
        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        try:
            # Load config should return None (inactive use case)
            config = await config_loader.load_config(str(use_case.id))
            assert config is None

        finally:
            # Cleanup
            await async_db_session.execute(delete(UseCase).where(UseCase.id == use_case.id))
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_load_config_no_config_json(
        self, config_loader, async_db_session, sample_use_case_data
    ):
        """Test loading config when use case has no config_json."""
        # Create use case without config_json
        use_case_data = sample_use_case_data.copy()
        use_case_data["config_json"] = None
        use_case = UseCase(**use_case_data)
        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        try:
            # Load config should return None (no config_json)
            config = await config_loader.load_config(str(use_case.id))
            assert config is None

        finally:
            # Cleanup
            await async_db_session.execute(delete(UseCase).where(UseCase.id == use_case.id))
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_config_caching(self, config_loader, async_db_session, sample_use_case_data):
        """Test that configs are properly cached."""
        # Create use case in database
        use_case = UseCase(**sample_use_case_data)
        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        try:
            # Load config first time
            config1 = await config_loader.load_config(str(use_case.id))
            assert config1 is not None

            # Load config second time (should hit cache)
            config2 = await config_loader.load_config(str(use_case.id))
            assert config2 is not None

            # Verify same object returned (cached)
            assert config1 is config2

            # Verify cache stats
            stats = config_loader.get_cache_stats()
            assert stats["use_case_cache_size"] == 1
            assert stats["total_cached_configs"] == 1

        finally:
            # Cleanup
            await async_db_session.execute(delete(UseCase).where(UseCase.id == use_case.id))
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_intent_caching(self, config_loader, async_db_session, sample_use_case_data):
        """Test that configs are properly cached by intent."""
        # Create use case in database
        use_case = UseCase(**sample_use_case_data)
        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        try:
            # Load config by intent first time
            config1 = await config_loader.load_config_by_intent(RequestType.QUERY)
            assert config1 is not None

            # Load config by intent second time (should hit cache)
            config2 = await config_loader.load_config_by_intent(RequestType.QUERY)
            assert config2 is not None

            # Verify same object returned (cached)
            assert config1 is config2

            # Verify cache stats
            stats = config_loader.get_cache_stats()
            assert stats["intent_cache_size"] == 1
            assert stats["total_cached_configs"] == 1

        finally:
            # Cleanup
            await async_db_session.execute(delete(UseCase).where(UseCase.id == use_case.id))
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, config_loader, async_db_session, sample_use_case_data):
        """Test cache invalidation functionality."""
        # Create use case in database
        use_case = UseCase(**sample_use_case_data)
        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        try:
            # Load config to cache it
            config = await config_loader.load_config(str(use_case.id))
            assert config is not None
            assert str(use_case.id) in config_loader._cache

            # Invalidate cache
            config_loader.invalidate_cache(use_case_id=str(use_case.id))
            assert str(use_case.id) not in config_loader._cache

        finally:
            # Cleanup
            await async_db_session.execute(delete(UseCase).where(UseCase.id == use_case.id))
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_preload_configs(
        self,
        config_loader,
        async_db_session,
        sample_use_case_data,
        sample_use_case_2_data,
    ):
        """Test preloading multiple configs."""
        # Create use cases in database
        use_case1 = UseCase(**sample_use_case_data)
        use_case2 = UseCase(**sample_use_case_2_data)
        async_db_session.add(use_case1)
        async_db_session.add(use_case2)
        await async_db_session.commit()
        await async_db_session.refresh(use_case1)
        await async_db_session.refresh(use_case2)

        try:
            # Preload configs by UUID
            await config_loader.preload_configs(
                use_case_ids=[
                    str(use_case1.id),
                    str(use_case2.id),
                ],
                intent_types=[RequestType.QUERY, RequestType.SUMMARIZATION],
            )

            # Verify configs were loaded
            assert str(use_case1.id) in config_loader._cache
            assert str(use_case2.id) in config_loader._cache
            assert "QUERY" in config_loader._cache_by_intent
            assert "SUMMARIZATION" in config_loader._cache_by_intent

            # Verify cache stats
            stats = config_loader.get_cache_stats()
            assert stats["use_case_cache_size"] == 2
            assert stats["intent_cache_size"] == 2
            assert stats["total_cached_configs"] == 4

        finally:
            # Cleanup
            await async_db_session.execute(
                delete(UseCase).where(UseCase.id.in_([use_case1.id, use_case2.id]))
            )
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_multiple_intent_types_same_config(
        self, config_loader, async_db_session, sample_use_case_data
    ):
        """Test loading config when multiple use cases have same intent type."""
        # Create first use case
        use_case1 = UseCase(**sample_use_case_data)
        async_db_session.add(use_case1)
        await async_db_session.commit()
        await async_db_session.refresh(use_case1)

        # Create second use case with same intent type
        use_case2_data = sample_use_case_data.copy()
        use_case2_data["use_case_id"] = "integration_test_use_case_2"
        use_case2_data["name"] = "Integration Test Use Case 2"
        use_case2 = UseCase(**use_case2_data)
        async_db_session.add(use_case2)
        await async_db_session.commit()
        await async_db_session.refresh(use_case2)

        try:
            # Load config by intent - should get first one
            config = await config_loader.load_config_by_intent(RequestType.QUERY)
            assert config is not None
            assert config.models.llm == "gpt-4o"

        finally:
            # Cleanup
            await async_db_session.execute(
                delete(UseCase).where(UseCase.id.in_([use_case1.id, use_case2.id]))
            )
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_database_error_handling(
        self, config_loader, async_db_session, sample_use_case_data
    ):
        """Test error handling when database operations fail."""
        # Create use case in database
        use_case = UseCase(**sample_use_case_data)
        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        try:
            # Close the session to simulate database error
            await async_db_session.close()

            # Load config should raise exception (SQLAlchemy raises InvalidRequestError for closed session)
            from sqlalchemy.exc import InvalidRequestError

            with pytest.raises(InvalidRequestError):
                await config_loader.load_config(str(use_case.id))

        finally:
            # Cleanup (reopen session for cleanup)
            from src.orchestrator.app.db.database import AsyncSessionLocal

            async with AsyncSessionLocal() as cleanup_session:
                result = await cleanup_session.execute(
                    select(UseCase).where(UseCase.id == use_case.id)
                )
                cleanup_use_case = result.scalar_one_or_none()
                if cleanup_use_case:
                    await cleanup_session.execute(delete(UseCase).where(UseCase.id == use_case.id))
                    await cleanup_session.commit()

    @pytest.mark.asyncio
    async def test_config_validation_integration(
        self, config_loader, async_db_session, sample_use_case_data
    ):
        """Test that loaded configs are properly validated against schema."""
        # Create use case in database
        use_case = UseCase(**sample_use_case_data)
        async_db_session.add(use_case)
        await async_db_session.commit()
        await async_db_session.refresh(use_case)

        try:
            # Load config
            config = await config_loader.load_config(str(use_case.id))

            # Verify all schema validation passed
            assert config is not None
            assert config.visibility.roles == ["analyst", "admin"]
            assert config.models.llm == "gpt-4o"
            assert config.generation_params.temperature == 0.7
            assert config.rag.enabled is True
            assert config.rag.top_k == 10
            assert config.output_contract.format.value == "text"
            assert config.telemetry.required_metrics == ["retrieval", "performance"]
            assert config.policy.streaming_enabled is True
            assert config.tools_allowlist == ["web_search"]

        finally:
            # Cleanup
            await async_db_session.execute(delete(UseCase).where(UseCase.id == use_case.id))
            await async_db_session.commit()

    @pytest.mark.asyncio
    async def test_get_default_config_integration(self, config_loader):
        """Test getting default config in integration context."""
        config = config_loader.get_default_config()

        # Verify default config is valid
        assert config is not None
        assert isinstance(config, UseCaseConfig)
        assert config.models.llm == "gpt-4o"
        assert config.rag.enabled is True
        assert config.policy.streaming_enabled is True
