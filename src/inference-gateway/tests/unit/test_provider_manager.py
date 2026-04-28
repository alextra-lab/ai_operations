"""
Unit tests for ProviderManager.

Tests provider loading, caching, and retrieval with 100% coverage target.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import ProviderConfig
from app.services.provider_manager import ProviderManager
from app.utils.errors import ProviderNotFoundError


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_providers():
    """Sample provider data from database."""
    return [
        {
            "id": "12345678-1234-1234-1234-123456789abc",
            "name": "openai",
            "provider_type": "openai_compatible",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test123",
            "is_enabled": True,
            "priority": 10,
            "config_json": {"org_id": "org-test"},
            "timeout_seconds": 30.0,
        },
        {
            "id": "23456789-2345-2345-2345-234567890abc",
            "name": "mistral",
            "provider_type": "openai_compatible",
            "base_url": "https://api.mistral.ai/v1",
            "api_key": "api-key-test",
            "is_enabled": True,
            "priority": 20,
            "config_json": {},
            "timeout_seconds": 30.0,
        },
        {
            "id": "34567890-3456-3456-3456-345678901abc",
            "name": "local",
            "provider_type": "openai_compatible",
            "base_url": "http://localhost:1234/v1",
            "api_key": None,
            "is_enabled": True,
            "priority": 100,
            "config_json": {"timeout_seconds": 60.0},
            "timeout_seconds": 60.0,  # Deprecated column, now in config_json
        },
        {
            "id": "45678901-4567-4567-4567-456789012abc",
            "name": "disabled_provider",
            "provider_type": "openai_compatible",
            "base_url": "https://disabled.example.com",
            "api_key": "test",
            "is_enabled": False,  # DISABLED
            "priority": 50,
            "config_json": {},
            "timeout_seconds": 30.0,
        },
    ]


@pytest.fixture
async def manager_with_data(mock_db_session, sample_providers):
    """ProviderManager pre-loaded with sample data."""
    from unittest.mock import Mock

    manager = ProviderManager()

    # Mock database query result
    # Only return enabled providers (is_enabled = true in SQL)
    enabled_providers = [p for p in sample_providers if p["is_enabled"]]

    mock_result = AsyncMock()
    mock_mappings = Mock()
    mock_mappings.all = Mock(return_value=enabled_providers)
    mock_result.mappings = Mock(return_value=mock_mappings)
    mock_db_session.execute.return_value = mock_result

    await manager.load_providers(mock_db_session)
    return manager


class TestProviderManager:
    """Test suite for ProviderManager class."""

    @pytest.mark.asyncio
    async def test_initial_state(self):
        """Test manager initial state."""
        manager = ProviderManager()
        assert not manager.is_loaded
        assert manager.get_cached_provider("any-provider") is None

    @pytest.mark.asyncio
    async def test_load_providers_from_db(self, mock_db_session, sample_providers):
        """Test loading providers from database."""
        manager = ProviderManager()

        # Mock database query (only enabled providers)
        enabled_providers = [p for p in sample_providers if p["is_enabled"]]
        mock_result = MagicMock()  # Use MagicMock not AsyncMock for sync methods
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = enabled_providers
        mock_result.mappings.return_value = mock_mappings
        mock_db_session.execute.return_value = mock_result

        await manager.load_providers(mock_db_session)

        # Verify loaded
        assert manager.is_loaded

        # Verify SQL query was executed
        mock_db_session.execute.assert_called_once()
        call_args = mock_db_session.execute.call_args
        sql = str(call_args[0][0])
        assert "gateway_providers" in sql.lower()
        assert "is_enabled = true" in sql.lower()

    @pytest.mark.asyncio
    async def test_get_provider_success(self, manager_with_data):
        """Test getting existing provider."""
        config = await manager_with_data.get_provider("openai")

        assert isinstance(config, ProviderConfig)
        assert config.name == "openai"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.is_enabled is True
        assert config.priority == 10

    @pytest.mark.asyncio
    async def test_get_provider_not_found(self, manager_with_data):
        """Test getting non-existent provider raises error."""
        with pytest.raises(ProviderNotFoundError) as exc_info:
            await manager_with_data.get_provider("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert exc_info.value.provider_name == "nonexistent"

    @pytest.mark.asyncio
    async def test_get_provider_auto_loads(self, mock_db_session, sample_providers):
        """Test get_provider() auto-loads if not loaded."""
        manager = ProviderManager()
        assert not manager.is_loaded

        # Mock database
        enabled_providers = [p for p in sample_providers if p["is_enabled"]]
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = enabled_providers
        mock_result.mappings.return_value = mock_mappings
        mock_db_session.execute.return_value = mock_result

        # Mock get_db context manager
        with patch("app.services.provider_manager.get_db") as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db_session

            config = await manager.get_provider("openai")

        assert config.name == "openai"
        assert manager.is_loaded

    @pytest.mark.asyncio
    async def test_list_providers_enabled_only(self, manager_with_data):
        """Test list_providers returns only enabled providers by default."""
        providers = await manager_with_data.list_providers(include_disabled=False)

        assert len(providers) == 3  # Only enabled ones
        names = [p.name for p in providers]
        assert "openai" in names
        assert "mistral" in names
        assert "local" in names
        assert "disabled_provider" not in names

    @pytest.mark.asyncio
    async def test_list_providers_sorted_by_priority(self, manager_with_data):
        """Test list_providers returns providers sorted by priority."""
        providers = await manager_with_data.list_providers()

        # Should be sorted by priority (ascending)
        assert providers[0].name == "openai"  # priority 10
        assert providers[1].name == "mistral"  # priority 20
        assert providers[2].name == "local"  # priority 100

    @pytest.mark.asyncio
    async def test_get_cached_provider(self, manager_with_data):
        """Test get_cached_provider returns cached value without DB query."""
        # Should return cached value
        config = manager_with_data.get_cached_provider("openai")
        assert config is not None
        assert config.name == "openai"

        # Non-existent provider returns None
        assert manager_with_data.get_cached_provider("nonexistent") is None

    @pytest.mark.asyncio
    async def test_reload(self, mock_db_session, sample_providers):
        """Test reload updates providers from database."""
        manager = ProviderManager()

        # Initial load
        enabled_providers = [p for p in sample_providers if p["is_enabled"]]
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = enabled_providers
        mock_result.mappings.return_value = mock_mappings
        mock_db_session.execute.return_value = mock_result
        await manager.load_providers(mock_db_session)

        assert len(await manager.list_providers()) == 3

        # Reload with updated data (only openai)
        updated_providers = [sample_providers[0]]  # Just openai
        mock_result2 = MagicMock()
        mock_mappings2 = MagicMock()
        mock_mappings2.all.return_value = updated_providers
        mock_result2.mappings.return_value = mock_mappings2

        # Verify updated (using mock_db_session for reload)
        with patch("app.services.provider_manager.get_db") as mock_get_db:
            mock_db_session.execute.return_value = mock_result2
            mock_get_db.return_value.__aenter__.return_value = mock_db_session
            await manager.reload()

        providers = await manager.list_providers()
        assert len(providers) == 1
        assert providers[0].name == "openai"

    @pytest.mark.asyncio
    async def test_empty_database(self, mock_db_session):
        """Test handling empty database (no providers)."""
        manager = ProviderManager()

        # Mock empty result
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = []
        mock_result.mappings.return_value = mock_mappings
        mock_db_session.execute.return_value = mock_result

        await manager.load_providers(mock_db_session)

        assert manager.is_loaded
        assert len(await manager.list_providers()) == 0

        # Should raise error for any provider
        with pytest.raises(ProviderNotFoundError):
            await manager.get_provider("any-provider")

    @pytest.mark.asyncio
    async def test_provider_config_parsing(self, manager_with_data):
        """Test ProviderConfig fields are correctly parsed."""
        config = await manager_with_data.get_provider("openai")

        # Verify all fields
        assert str(config.id) == "12345678-1234-1234-1234-123456789abc"
        assert config.name == "openai"
        assert config.provider_type == "openai_compatible"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.api_key == "sk-test123"
        assert config.is_enabled is True
        assert config.priority == 10
        assert config.config_json == {"org_id": "org-test"}
        assert config.timeout_seconds == 30.0

    @pytest.mark.asyncio
    async def test_provider_without_api_key(self, manager_with_data):
        """Test provider without API key (local provider)."""
        config = await manager_with_data.get_provider("local")

        assert config.name == "local"
        assert config.api_key is None  # Local provider has no API key
        assert config.timeout_seconds == 60.0

    @pytest.mark.asyncio
    async def test_disabled_provider_not_in_cache(self, mock_db_session, sample_providers):
        """Test disabled providers are not loaded into cache."""
        manager = ProviderManager()

        # Database query filters enabled only (SQL: is_enabled = true)
        enabled_providers = [p for p in sample_providers if p["is_enabled"]]
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.all.return_value = enabled_providers
        mock_result.mappings.return_value = mock_mappings
        mock_db_session.execute.return_value = mock_result

        await manager.load_providers(mock_db_session)

        # Disabled provider should not be in cache
        assert manager.get_cached_provider("disabled_provider") is None

        # Trying to get it should raise ProviderNotFoundError
        with pytest.raises(ProviderNotFoundError):
            await manager.get_provider("disabled_provider")
