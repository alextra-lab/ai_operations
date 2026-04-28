"""
Unit tests for SimpleRouter.

Tests model → provider routing logic with 100% coverage target.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.router import SimpleRouter
from app.utils.errors import ModelNotFoundError


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_models():
    """Sample model data."""
    return [
        ("gpt-4o-mini", "openai"),
        ("gpt-4o", "openai"),
        ("mistral-large-latest", "mistral"),
        ("llama-3-70b", "local"),
    ]


@pytest.fixture
async def router_with_data(mock_db_session, sample_models):
    """Router pre-loaded with sample data."""
    router = SimpleRouter()

    # Mock database query result - fetchall() is synchronous
    mock_result = AsyncMock()
    mock_result.fetchall = lambda: sample_models
    mock_db_session.execute.return_value = mock_result

    await router.load_routes(mock_db_session)
    return router


class TestSimpleRouter:
    """Test suite for SimpleRouter class."""

    @pytest.mark.asyncio
    async def test_initial_state(self):
        """Test router initial state."""
        router = SimpleRouter()
        assert not router.is_loaded
        assert router.get_cached_route("any-model") is None

    @pytest.mark.asyncio
    async def test_load_routes_from_db(self, mock_db_session, sample_models):
        """Test loading routes from database."""
        router = SimpleRouter()

        # Mock database query - fetchall() is synchronous for text() queries
        mock_result = AsyncMock()
        mock_result.fetchall = lambda: sample_models  # Make fetchall() synchronous
        mock_db_session.execute.return_value = mock_result

        await router.load_routes(mock_db_session)

        # Verify loaded
        assert router.is_loaded
        assert len(await router.list_models()) == 4

        # Verify SQL query was executed
        mock_db_session.execute.assert_called_once()
        call_args = mock_db_session.execute.call_args
        sql = str(call_args[0][0])
        assert "models" in sql.lower()
        assert "is_available = true" in sql.lower()  # Changed from is_active to match actual schema

    @pytest.mark.asyncio
    async def test_route_known_model(self, router_with_data):
        """Test routing known model to provider."""
        provider = await router_with_data.route("gpt-4o-mini")
        assert provider == "openai"

        provider = await router_with_data.route("mistral-large-latest")
        assert provider == "mistral"

        provider = await router_with_data.route("llama-3-70b")
        assert provider == "local"

    @pytest.mark.asyncio
    async def test_route_unknown_model(self, router_with_data):
        """Test routing unknown model raises ModelNotFoundError."""
        with pytest.raises(ModelNotFoundError) as exc_info:
            await router_with_data.route("unknown-model")

        assert "unknown-model" in str(exc_info.value)
        assert exc_info.value.model_id == "unknown-model"

    @pytest.mark.asyncio
    async def test_route_auto_loads(self, mock_db_session, sample_models):
        """Test route() auto-loads if not loaded."""
        router = SimpleRouter()
        assert not router.is_loaded

        # Mock database - fetchall() is synchronous
        mock_result = AsyncMock()
        mock_result.fetchall = lambda: sample_models
        mock_db_session.execute.return_value = mock_result

        # Mock get_db context manager
        with patch("app.services.router.get_db") as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session

            provider = await router.route("gpt-4o-mini")

        assert provider == "openai"
        assert router.is_loaded

    @pytest.mark.asyncio
    async def test_get_cached_route(self, router_with_data):
        """Test get_cached_route returns cached value without DB query."""
        # Should return cached value
        assert router_with_data.get_cached_route("gpt-4o-mini") == "openai"
        assert router_with_data.get_cached_route("unknown-model") is None

    @pytest.mark.asyncio
    async def test_list_models(self, router_with_data):
        """Test list_models returns all model IDs."""
        models = await router_with_data.list_models()

        assert len(models) == 4
        assert "gpt-4o-mini" in models
        assert "mistral-large-latest" in models
        assert sorted(models) == models  # Should be sorted

    @pytest.mark.asyncio
    async def test_get_route_map(self, router_with_data):
        """Test get_route_map returns full mapping."""
        route_map = await router_with_data.get_route_map()

        assert len(route_map) == 4
        assert route_map["gpt-4o-mini"] == "openai"
        assert route_map["mistral-large-latest"] == "mistral"
        assert route_map["llama-3-70b"] == "local"

    @pytest.mark.asyncio
    async def test_reload(self, mock_db_session, sample_models):
        """Test reload updates routes from database."""
        router = SimpleRouter()

        # Initial load - fetchall() is synchronous
        mock_result = AsyncMock()
        mock_result.fetchall = lambda: sample_models
        mock_db_session.execute.return_value = mock_result
        await router.load_routes(mock_db_session)

        assert len(await router.list_models()) == 4

        # Reload with updated data
        updated_models = [
            ("gpt-4o-mini", "openai"),
            ("new-model", "openai"),
        ]

        # Update mock for reload
        mock_result2 = AsyncMock()
        mock_result2.fetchall = lambda: updated_models

        # Mock get_db for reload
        with patch("app.services.router.get_db") as mock_get_db:
            mock_db_session.execute.return_value = mock_result2
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            await router.reload()

        # Verify updated
        assert len(await router.list_models()) == 2
        assert "new-model" in await router.list_models()
        assert "mistral-large-latest" not in await router.list_models()

    @pytest.mark.asyncio
    async def test_empty_database(self, mock_db_session):
        """Test handling empty database (no models)."""
        router = SimpleRouter()

        # Mock empty result - fetchall() is synchronous
        mock_result = AsyncMock()
        mock_result.fetchall = lambda: []
        mock_db_session.execute.return_value = mock_result

        await router.load_routes(mock_db_session)

        assert router.is_loaded
        assert len(await router.list_models()) == 0

        # Should raise error for any model
        with pytest.raises(ModelNotFoundError):
            await router.route("any-model")

    @pytest.mark.asyncio
    async def test_performance_cached_lookup(self, router_with_data):
        """Test cached lookup is fast (performance verification)."""
        import time

        # Cached lookup should be <1ms
        start = time.perf_counter()
        for _ in range(1000):
            router_with_data.get_cached_route("gpt-4o-mini")
        elapsed_ms = (time.perf_counter() - start) * 1000

        # 1000 lookups should be <1ms total (dict lookup is O(1))
        assert elapsed_ms < 10  # Very generous upper bound
