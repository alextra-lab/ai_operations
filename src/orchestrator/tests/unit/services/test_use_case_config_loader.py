"""
Unit tests for UseCaseConfigLoader service.

Tests the configuration loading, caching, and error handling functionality
of the UseCaseConfigLoader service.
"""

from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.orchestrator.app.db.models import UseCase
from src.orchestrator.app.schemas.intent import RequestType
from src.orchestrator.app.schemas.use_case_config import UseCaseConfig
from src.orchestrator.app.services.use_case_config_loader import (
    UseCaseConfigLoader,
    clear_global_cache,
    get_config_loader,
    invalidate_config_cache_for_use_case,
)


class TestUseCaseConfigLoader:
    """Test UseCaseConfigLoader functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def config_loader(self, mock_db_session):
        """Create a UseCaseConfigLoader instance with mock session."""
        return UseCaseConfigLoader(mock_db_session)

    @pytest.fixture
    def sample_use_case(self):
        """Create a sample use case for testing."""
        use_case = Mock(spec=UseCase)
        use_case.use_case_id = "test_use_case"
        use_case.intent_type = "QUERY"
        use_case.is_active = True
        use_case.config_json = {
            "visibility": {"roles": ["analyst"], "tags": ["test"]},
            "models": {"llm": "gpt-4o", "embedding": "text-embedding-3-small"},
            "generation_params": {
                "sampling_preset": "custom",
                "temperature": 0.7,
                "max_tokens": 1024,
            },
            "rag": {"enabled": True, "top_k": 10, "vector_collections": ["documents"]},
            "output_contract": {"format": "text"},
            "telemetry": {"required_metrics": ["retrieval"]},
            "policy": {"streaming_enabled": True},
            "tools_allowlist": [],
        }
        return use_case

    def test_init(self, mock_db_session):
        """Test UseCaseConfigLoader initialization."""
        loader = UseCaseConfigLoader(mock_db_session)
        assert loader.db_session == mock_db_session
        assert loader._cache == {}
        assert loader._cache_by_intent == {}

    def test_load_config_success(self, config_loader, sample_use_case):
        """Test successful config loading by use_case_id."""
        # Mock database query
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )

        # Load config
        config = config_loader.load_config("test_use_case")

        # Verify config was loaded and cached
        assert config is not None
        assert isinstance(config, UseCaseConfig)
        assert config.models.llm == "gpt-4o"
        assert config.rag.top_k == 10
        assert "test_use_case" in config_loader._cache

    def test_load_config_not_found(self, config_loader):
        """Test config loading when use case not found."""
        # Mock database query returning None
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = None

        # Load config
        config = config_loader.load_config("nonexistent")

        # Verify None returned and not cached
        assert config is None
        assert "nonexistent" not in config_loader._cache

    def test_load_config_inactive_no_config(self, config_loader):
        """Test config loading when use case is inactive and has no config_json.

        ADR-070: is_active gates discovery, not execution. load_config(uuid)
        no longer filters by is_active. The row is returned but config_json=None
        still yields None.
        """
        inactive_use_case = Mock(spec=UseCase)
        inactive_use_case.is_active = False
        inactive_use_case.config_json = None
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            inactive_use_case
        )

        config = config_loader.load_config("inactive_use_case")

        # None because config_json is None (not because of is_active)
        assert config is None

    def test_load_config_no_config_json(self, config_loader):
        """Test config loading when use case has no config_json."""
        # Mock use case with no config_json
        use_case = Mock(spec=UseCase)
        use_case.use_case_id = "no_config"
        use_case.is_active = True
        use_case.config_json = None
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            use_case
        )

        # Load config
        config = config_loader.load_config("no_config")

        # Verify None returned
        assert config is None

    def test_load_config_empty_use_case_id(self, config_loader):
        """Test config loading with empty use_case_id."""
        with pytest.raises(ValueError, match="use_case_id cannot be empty or None"):
            config_loader.load_config("")

        with pytest.raises(ValueError, match="use_case_id cannot be empty or None"):
            config_loader.load_config(None)

    def test_load_config_database_error(self, config_loader):
        """Test config loading with database error."""
        # Mock database error
        config_loader.db_session.query.side_effect = SQLAlchemyError("Database error")

        # Load config should raise exception
        with pytest.raises(SQLAlchemyError):
            config_loader.load_config("test_use_case")

    def test_load_config_by_intent_success(self, config_loader, sample_use_case):
        """Test successful config loading by intent type."""
        # Mock database query
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )

        # Load config by intent
        config = config_loader.load_config_by_intent(RequestType.QUERY)

        # Verify config was loaded and cached
        assert config is not None
        assert isinstance(config, UseCaseConfig)
        assert config.models.llm == "gpt-4o"
        assert "QUERY" in config_loader._cache_by_intent

    def test_load_config_by_intent_not_found(self, config_loader):
        """Test config loading by intent when no use case found."""
        # Mock database query returning None
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = None

        # Load config by intent
        config = config_loader.load_config_by_intent(RequestType.SUMMARIZATION)

        # Verify None returned and not cached
        assert config is None
        assert "SUMMARIZATION" not in config_loader._cache_by_intent

    def test_load_config_by_intent_none_intent(self, config_loader):
        """Test config loading by intent with None intent_type."""
        with pytest.raises(ValueError, match="intent_type cannot be None"):
            config_loader.load_config_by_intent(None)

    def test_get_default_config(self, config_loader):
        """Test getting default configuration."""
        config = config_loader.get_default_config()

        assert isinstance(config, UseCaseConfig)
        assert config.models.llm == "gpt-4o"
        assert config.rag.enabled is True

    def test_invalidate_cache_by_use_case_id(self, config_loader, sample_use_case):
        """Test cache invalidation by use_case_id."""
        # Load and cache a config
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )
        config_loader.load_config("test_use_case")

        # Verify it's cached
        assert "test_use_case" in config_loader._cache

        # Invalidate specific use_case_id
        config_loader.invalidate_cache(use_case_id="test_use_case")

        # Verify it's removed from cache
        assert "test_use_case" not in config_loader._cache

    def test_invalidate_cache_by_intent_type(self, config_loader, sample_use_case):
        """Test cache invalidation by intent_type."""
        # Load and cache a config by intent
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )
        config_loader.load_config_by_intent(RequestType.QUERY)

        # Verify it's cached
        assert "QUERY" in config_loader._cache_by_intent

        # Invalidate specific intent_type
        config_loader.invalidate_cache(intent_type=RequestType.QUERY)

        # Verify it's removed from cache
        assert "QUERY" not in config_loader._cache_by_intent

    def test_invalidate_all_cache(self, config_loader, sample_use_case):
        """Test invalidating all cache."""
        # Load and cache configs
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )
        config_loader.load_config("test_use_case")
        config_loader.load_config_by_intent(RequestType.QUERY)

        # Verify they're cached
        assert "test_use_case" in config_loader._cache
        assert "QUERY" in config_loader._cache_by_intent

        # Invalidate all cache
        config_loader.invalidate_cache()

        # Verify all cache is cleared
        assert len(config_loader._cache) == 0
        assert len(config_loader._cache_by_intent) == 0

    def test_clear_cache(self, config_loader, sample_use_case):
        """Test clearing all cache."""
        # Load and cache configs
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )
        config_loader.load_config("test_use_case")
        config_loader.load_config_by_intent(RequestType.QUERY)

        # Verify they're cached
        assert len(config_loader._cache) > 0
        assert len(config_loader._cache_by_intent) > 0

        # Clear cache
        config_loader.clear_cache()

        # Verify all cache is cleared
        assert len(config_loader._cache) == 0
        assert len(config_loader._cache_by_intent) == 0

    def test_get_cache_stats(self, config_loader, sample_use_case):
        """Test getting cache statistics."""
        # Initially empty
        stats = config_loader.get_cache_stats()
        assert stats["use_case_cache_size"] == 0
        assert stats["intent_cache_size"] == 0
        assert stats["total_cached_configs"] == 0

        # Load and cache configs
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )
        config_loader.load_config("test_use_case")
        config_loader.load_config_by_intent(RequestType.QUERY)

        # Check stats after caching
        stats = config_loader.get_cache_stats()
        assert stats["use_case_cache_size"] == 1
        assert stats["intent_cache_size"] == 1
        assert stats["total_cached_configs"] == 2

    def test_preload_configs_by_use_case_ids(self, config_loader, sample_use_case):
        """Test preloading configs by specific use_case_ids."""
        # Mock database query
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )

        # Preload specific use case IDs
        config_loader.preload_configs(use_case_ids=["test_use_case"])

        # Verify config was loaded
        assert "test_use_case" in config_loader._cache

    def test_preload_configs_by_intent_types(self, config_loader, sample_use_case):
        """Test preloading configs by specific intent_types."""
        # Mock database query
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )

        # Preload specific intent types
        config_loader.preload_configs(intent_types=[RequestType.QUERY])

        # Verify config was loaded
        assert "QUERY" in config_loader._cache_by_intent

    def test_preload_configs_all_active(self, config_loader, sample_use_case):
        """Test preloading all active configs."""
        # Mock database queries
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )
        config_loader.db_session.query.return_value.filter.return_value.all.return_value = [
            sample_use_case
        ]

        # Mock the distinct query for intent types
        mock_distinct_query = Mock()
        mock_distinct_query.all.return_value = [("QUERY",)]
        config_loader.db_session.query.return_value.filter.return_value.distinct.return_value = (
            mock_distinct_query
        )

        # Preload all active configs
        config_loader.preload_configs()

        # Verify configs were loaded
        assert "test_use_case" in config_loader._cache
        assert "QUERY" in config_loader._cache_by_intent

    def test_cache_hit_use_case_id(self, config_loader, sample_use_case):
        """Test cache hit for use_case_id."""
        # Load config first time
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )
        config1 = config_loader.load_config("test_use_case")

        # Load config second time (should hit cache)
        config2 = config_loader.load_config("test_use_case")

        # Verify same object returned (cached)
        assert config1 is config2

        # Verify database was only queried once
        assert config_loader.db_session.query.call_count == 1

    def test_cache_hit_intent_type(self, config_loader, sample_use_case):
        """Test cache hit for intent_type."""
        # Load config first time
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )
        config1 = config_loader.load_config_by_intent(RequestType.QUERY)

        # Load config second time (should hit cache)
        config2 = config_loader.load_config_by_intent(RequestType.QUERY)

        # Verify same object returned (cached)
        assert config1 is config2

        # Verify database was only queried once
        assert config_loader.db_session.query.call_count == 1


class TestGlobalConfigLoaderFunctions:
    """Test global config loader functions."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    def test_get_config_loader_new_instance(self, mock_db_session):
        """Test getting a new config loader instance."""
        loader = get_config_loader(mock_db_session)

        assert isinstance(loader, UseCaseConfigLoader)
        assert loader.db_session == mock_db_session

    def test_get_config_loader_cached_instance(self, mock_db_session):
        """Test getting a cached config loader instance."""
        cache_key = "test_cache_key"

        # Get first instance
        loader1 = get_config_loader(mock_db_session, cache_key)

        # Get second instance with same cache key
        loader2 = get_config_loader(mock_db_session, cache_key)

        # Verify same instance returned
        assert loader1 is loader2

    def test_clear_global_cache(self, mock_db_session):
        """Test clearing global cache."""
        cache_key = "test_cache_key"

        # Get cached instance
        get_config_loader(mock_db_session, cache_key)

        # Clear global cache
        clear_global_cache()

        # Get new instance with same cache key
        loader = get_config_loader(mock_db_session, cache_key)

        # Verify it's a new instance
        assert isinstance(loader, UseCaseConfigLoader)

    def test_invalidate_config_cache_for_use_case_clears_process_cache(self):
        """Process-wide config cache is cleared for the given use case id (e.g. after PATCH)."""
        from src.orchestrator.app.services import use_case_config_loader

        cache = use_case_config_loader._config_cache_by_uuid
        test_id = "test-uuid-for-invalidation"
        try:
            cache[test_id] = UseCaseConfig.get_default_config()
            assert test_id in cache

            invalidate_config_cache_for_use_case(test_id)

            assert test_id not in cache
        finally:
            cache.pop(test_id, None)

    def test_invalidate_config_cache_for_use_case_missing_key_no_op(self):
        """Invalidating a non-cached use case id is a no-op (does not raise)."""
        invalidate_config_cache_for_use_case("nonexistent-uuid-12345")


class TestUseCaseConfigLoaderIntegration:
    """Integration tests for UseCaseConfigLoader."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def config_loader(self, mock_db_session):
        """Create a UseCaseConfigLoader instance with mock session."""
        return UseCaseConfigLoader(mock_db_session)

    @pytest.fixture
    def sample_use_case(self):
        """Create a sample use case for testing."""
        use_case = Mock(spec=UseCase)
        use_case.use_case_id = "test_use_case"
        use_case.intent_type = "QUERY"
        use_case.is_active = True
        use_case.config_json = {
            "visibility": {"roles": ["analyst"], "tags": ["test"]},
            "models": {"llm": "gpt-4o", "embedding": "text-embedding-3-small"},
            "generation_params": {
                "sampling_preset": "custom",
                "temperature": 0.7,
                "max_tokens": 1024,
            },
            "rag": {"enabled": True, "top_k": 10, "vector_collections": ["documents"]},
            "output_contract": {"format": "text"},
            "telemetry": {"required_metrics": ["retrieval"]},
            "policy": {"streaming_enabled": True},
            "tools_allowlist": [],
        }
        return use_case

    def test_load_config_with_real_schema(self, config_loader, sample_use_case):
        """Test loading config with real UseCaseConfig schema validation."""
        # Mock database query
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )

        # Load config
        config = config_loader.load_config("test_use_case")

        # Verify config is properly validated
        assert config is not None
        assert config.models.llm == "gpt-4o"
        assert config.rag.enabled is True
        assert config.rag.top_k == 10
        assert config.generation_params.temperature == 0.7
        assert config.policy.streaming_enabled is True

    def test_load_config_invalid_json_raises_error(self, config_loader):
        """Test loading config with invalid JSON raises error."""
        # Mock use case with invalid config_json
        use_case = Mock(spec=UseCase)
        use_case.use_case_id = "invalid_config"
        use_case.is_active = True
        use_case.config_json = {"invalid": "config"}  # Missing required fields
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            use_case
        )

        # Load config should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            config_loader.load_config("invalid_config")

    def test_load_config_by_intent_with_real_schema(self, config_loader, sample_use_case):
        """Test loading config by intent with real UseCaseConfig schema validation."""
        # Mock database query
        config_loader.db_session.query.return_value.filter.return_value.first.return_value = (
            sample_use_case
        )

        # Load config by intent
        config = config_loader.load_config_by_intent(RequestType.QUERY)

        # Verify config is properly validated
        assert config is not None
        assert config.models.llm == "gpt-4o"
        assert config.rag.enabled is True
        assert config.rag.top_k == 10
        assert config.generation_params.temperature == 0.7
        assert config.policy.streaming_enabled is True
